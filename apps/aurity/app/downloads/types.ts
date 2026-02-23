export interface PlatformAsset {
  url: string;
  size: string;
  sha256: string;
}

export interface Release {
  version: string;
  date: string;
  platforms: {
    macos?: PlatformAsset;
    windows?: PlatformAsset;
    linux?: PlatformAsset;
  };
  changelog?: string[];
}

export interface ReleasesData {
  releases: Release[];
  generatedAt: string;
  source: string;
}

export interface Benefit {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  stat: string;
}

export interface FAQ {
  question: string;
  answer: string;
}

export interface DemoStep {
  id: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  duration: string;
  description: string;
}

export interface SystemRequirements {
  os: string;
  cpu: string;
  ram: string;
  disk: string;
}
