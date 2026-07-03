import React from 'react';

const ProgressRing = ({ 
  radius = 40, 
  stroke = 8, 
  progress = 0, 
  color = 'stroke-brand-500',
  trackColor = 'stroke-slate-200 dark:stroke-slate-800'
}) => {
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (Math.min(100, Math.max(0, progress)) / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center">
      <svg
        height={radius * 2}
        width={radius * 2}
        className="transform -rotate-90"
      >
        <circle
          className={`${trackColor} transition-all duration-300`}
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          className={`${color} progress-ring-circle transition-all duration-500 ease-out`}
          fill="transparent"
          strokeWidth={stroke}
          strokeDasharray={circumference + ' ' + circumference}
          style={{ strokeDashoffset }}
          strokeLinecap="round"
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
      </svg>
      <div className="absolute text-center">
        <span className="text-sm font-bold text-slate-800 dark:text-white">
          {Math.round(progress)}%
        </span>
      </div>
    </div>
  );
};

export default ProgressRing;
