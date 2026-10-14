// lucide-react.d.ts
// Lucide React icons don't ship TypeScript declarations in the installed version.
// This ambient declaration allows the module to be imported without type errors.
// Icons are typed as `any` since they're SVG components with runtime props.

declare module 'lucide-react' {
  import type { FC, SVGProps } from 'react';

  type LucideIconProps = SVGProps<SVGSVGElement> & {
    size?: string | number;
    strokeWidth?: string | number;
    absoluteStrokeWidth?: boolean;
    color?: string;
  };

  type IconComponent = FC<LucideIconProps>;

  export const ArrowDownRight: IconComponent;
  export const ArrowRight: IconComponent;
  export const ArrowUpRight: IconComponent;
  export const Bookmark: IconComponent;
  export const Camera: IconComponent;
  export const ChevronLeft: IconComponent;
  export const ChevronRight: IconComponent;
  export const CircleHelp: IconComponent;
  export const Eye: IconComponent;
  export const LockKeyhole: IconComponent;
  export const LogOut: IconComponent;
  export const Menu: IconComponent;
  export const Pause: IconComponent;
  export const Play: IconComponent;
  export const RefreshCw: IconComponent;
  export const Search: IconComponent;
  export const Sparkles: IconComponent;
  export const Trash2: IconComponent;
  export const Upload: IconComponent;
  export const User: IconComponent;
  export const Volume2: IconComponent;
  export const VolumeX: IconComponent;
  export const X: IconComponent;
}