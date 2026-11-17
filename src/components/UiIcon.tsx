import React from 'react';
import type { ThemeMode, UiIconName } from '../types/rag';

interface UiIconProps {
  name: UiIconName;
  theme: ThemeMode;
  size?: number;
  alt?: string;
  className?: string;
}

export const UiIcon: React.FC<UiIconProps> = ({
  name,
  theme,
  size = 18,
  alt = '',
  className = '',
}) => {
  const folder = theme === 'dark' ? 'dark' : 'light';
  return (
    <img
      src={`/ui/${folder}/${name}.svg`}
      alt={alt}
      width={size}
      height={size}
      style={{ width: size, height: size }}
      className={`shrink-0 select-none ${className}`}
      referrerPolicy="no-referrer"
    />
  );
};
