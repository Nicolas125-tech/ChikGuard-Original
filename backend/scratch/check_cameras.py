import cv2

def list_cameras():
    index = 0
    arr = []
    while index < 5:
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.read()[0]:
            print(f"CAMERA FOUND AT INDEX: {index}")
            arr.append(index)
            cap.release()
        else:
            print(f"NO CAMERA AT INDEX: {index}")
            cap.release()
        index += 1
    return arr

if __name__ == "__main__":
    print("Listing available cameras (DSHOW)...")
    list_cameras()
