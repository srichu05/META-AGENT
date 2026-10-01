import React from 'react';

export const ChromeEmblem = ({ size = 380, className = '' }) => {
  return (
    <div
      style={{
        width: `${size}px`,
        height: `${size}px`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        filter: 'drop-shadow(0 20px 40px rgba(0, 0, 0, 0.9))',
      }}
      className={className}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 400 400"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', height: '100%' }}
      >
        <defs>
          {/* Chrome Facet Gradients */}
          <linearGradient id="chrome_top" x1="50" y1="50" x2="350" y2="200" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="25%" stopColor="#E2E8F0" />
            <stop offset="50%" stopColor="#94A3B8" />
            <stop offset="75%" stopColor="#CBD5E1" />
            <stop offset="100%" stopColor="#475569" />
          </linearGradient>

          <linearGradient id="chrome_facet_light" x1="100" y1="80" x2="280" y2="240" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#F8FAFC" />
            <stop offset="40%" stopColor="#E2E8F0" />
            <stop offset="70%" stopColor="#94A3B8" />
            <stop offset="100%" stopColor="#64748B" />
          </linearGradient>

          <linearGradient id="chrome_facet_dark" x1="150" y1="120" x2="320" y2="340" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#94A3B8" />
            <stop offset="50%" stopColor="#475569" />
            <stop offset="85%" stopColor="#1E293B" />
            <stop offset="100%" stopColor="#0F172A" />
          </linearGradient>

          <linearGradient id="chrome_edge_highlight" x1="80" y1="60" x2="220" y2="180" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.9" />
            <stop offset="50%" stopColor="#FFFFFF" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0.05" />
          </linearGradient>

          <radialGradient id="specular_glow" cx="35%" cy="30%" r="50%">
            <stop offset="0%" stopColor="rgba(255, 255, 255, 0.4)" />
            <stop offset="60%" stopColor="rgba(255, 255, 255, 0)" />
          </radialGradient>
        </defs>

        {/* Outer Faceted Geometric S-Form (Reflecting ui.ssych.com chrome emblem) */}
        {/* Upper Chevron / Wing */}
        <path
          d="M120 70 L280 70 C310 70 330 90 315 125 L235 220 L300 220 C330 220 345 245 325 285 L260 350 L100 350 C70 350 55 330 75 295 L155 200 L95 200 C65 200 50 175 70 135 Z"
          fill="url(#chrome_facet_light)"
        />

        {/* 3D Bevel Facet Top */}
        <path
          d="M120 70 L280 70 L250 110 L150 110 Z"
          fill="url(#chrome_top)"
        />

        {/* 3D Bevel Facet Diagonal Upper */}
        <path
          d="M280 70 L315 125 L235 220 L210 185 L250 110 Z"
          fill="url(#chrome_facet_dark)"
        />

        {/* Central Cross Diagonal Fold */}
        <path
          d="M235 220 L300 220 L325 285 L260 350 L220 310 L250 250 L180 250 L155 200 Z"
          fill="url(#chrome_facet_light)"
        />

        {/* Lower Bevel Under */}
        <path
          d="M260 350 L100 350 L130 310 L220 310 Z"
          fill="url(#chrome_facet_dark)"
        />

        {/* Lower Left Wing Inset */}
        <path
          d="M100 350 L75 295 L155 200 L180 250 L130 310 Z"
          fill="url(#chrome_top)"
        />

        {/* Specular Edge Highlights */}
        <path
          d="M120 70 L280 70 L315 125"
          stroke="url(#chrome_edge_highlight)"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <path
          d="M235 220 L300 220 L325 285"
          stroke="url(#chrome_edge_highlight)"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <path
          d="M75 295 L155 200 L95 200"
          stroke="rgba(255,255,255,0.7)"
          strokeWidth="1.5"
        />

        {/* Soft Radial Ambient Specular Highlight */}
        <circle cx="160" cy="140" r="90" fill="url(#specular_glow)" pointerEvents="none" />
      </svg>
    </div>
  );
};

export default ChromeEmblem;
