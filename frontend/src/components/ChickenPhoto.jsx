import React from 'react';

const ChickenPhoto = ({ size = 17, className = '' }) => {
  const isActive = className.includes('text-emerald-400');

  return (
    <img
      src="/logo.jpeg"
      alt="Chicken"
      style={{
        width: size,
        height: size,
        filter: isActive ? 'none' : 'grayscale(100%) opacity(0.6)'
      }}
      className={`object-cover rounded-md transition-all duration-200 ${className.replace(/text-[a-z0-9-]+/g, '')}`}
    />
  );
};

export default ChickenPhoto;
