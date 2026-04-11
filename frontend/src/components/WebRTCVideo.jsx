import React, { useEffect, useRef } from 'react';

export default function WebRTCVideo({ url, className, onConnectionStateChange }) {
  const videoRef = useRef(null);
  const callbackRef = useRef(onConnectionStateChange);

  useEffect(() => {
    callbackRef.current = onConnectionStateChange;
  }, [onConnectionStateChange]);

  useEffect(() => {
    const config = {
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
    };
    let pc = new RTCPeerConnection(config);
    let timeoutId;
    let fallbackTriggered = false;

    const triggerFallback = () => {
      if (!fallbackTriggered) {
        fallbackTriggered = true;
        if (callbackRef.current) {
          callbackRef.current('failed');
        }
      }
    };

    timeoutId = setTimeout(() => {
      console.warn("WebRTC Watchdog timeout: no connection established in 6s.");
      triggerFallback();
    }, 6000);

    const startWebRTC = async () => {
      pc.addTransceiver('video', { direction: 'recvonly' });

      pc.addEventListener('track', (evt) => {
        if (evt.track.kind === 'video') {
          if (videoRef.current) {
            videoRef.current.srcObject = evt.streams[0];
          }
        }
      });

      pc.addEventListener('connectionstatechange', () => {
        console.log('WebRTC connection state:', pc.connectionState);
        if (pc.connectionState === 'connected') {
          clearTimeout(timeoutId);
        }
        if (callbackRef.current && !fallbackTriggered) {
          callbackRef.current(pc.connectionState);
        }
      });

      try {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        // Wait for ICE gathering to complete before sending the offer
        await new Promise((resolve) => {
          if (pc.iceGatheringState === 'complete') {
            resolve();
          } else {
            const checkState = () => {
              if (pc.iceGatheringState === 'complete') {
                pc.removeEventListener('icegatheringstatechange', checkState);
                resolve();
              }
            };
            pc.addEventListener('icegatheringstatechange', checkState);
            // Fallback timeout just in case it takes too long
            setTimeout(() => {
              pc.removeEventListener('icegatheringstatechange', checkState);
              resolve();
            }, 3000);
          }
        });

        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            sdp: pc.localDescription.sdp,
            type: pc.localDescription.type,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to send WebRTC offer');
        }

        const answer = await response.json();
        await pc.setRemoteDescription(answer);
      } catch (err) {
        console.error('WebRTC negotiation error:', err);
        triggerFallback();
      }
    };

    startWebRTC();

    return () => {
      clearTimeout(timeoutId);
      pc.close();
    };
  }, [url]);

  return <video ref={videoRef} className={className} autoPlay playsInline muted />;
}
