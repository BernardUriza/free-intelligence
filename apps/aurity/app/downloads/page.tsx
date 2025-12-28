/**
 * Downloads Page
 *
 * Displays available Aurity Desktop releases for download.
 * Fetches release information from /api/releases endpoint.
 */

'use client';

import { useState, useEffect } from 'react';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { Button } from '@/components/ui/button';
import {
  Download,
  Apple,
  Monitor,
  Shield,
  Cpu,
  HardDrive,
  RefreshCw,
  CheckCircle,
  ExternalLink,
} from 'lucide-react';

interface Release {
  version: string;
  date: string;
  platforms: {
    macos?: {
      url: string;
      size: string;
      sha256: string;
    };
    linux?: {
      url: string;
      size: string;
      sha256: string;
    };
  };
  changelog?: string[];
}

const features = [
  {
    icon: Shield,
    title: '100% Offline',
    description: 'All AI processing happens on your device. No data leaves your computer.',
  },
  {
    icon: Cpu,
    title: 'Local LLM',
    description: 'Powered by Ollama with Qwen3, Llama, or your preferred model.',
  },
  {
    icon: HardDrive,
    title: 'Your Data',
    description: 'Medical records stored locally in ~/.aurity with full encryption.',
  },
];

const systemRequirements = {
  macos: {
    os: 'macOS 12.0 (Monterey) or later',
    cpu: 'Apple Silicon (M1/M2/M3) or Intel',
    ram: '8 GB minimum, 16 GB recommended',
    disk: '10 GB free space',
  },
  linux: {
    os: 'Ubuntu 22.04 LTS or compatible',
    cpu: 'x86_64 processor',
    ram: '8 GB minimum, 16 GB recommended',
    disk: '10 GB free space',
  },
};

export default function DownloadsPage() {
  const [releases, setReleases] = useState<Release[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReleases();
  }, []);

  const fetchReleases = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/releases');
      if (!response.ok) {
        throw new Error('Failed to fetch releases');
      }
      const data = await response.json();
      setReleases(data.releases || []);
    } catch (err) {
      console.error('Failed to fetch releases:', err);
      // Use placeholder data if API fails
      setReleases([
        {
          version: '1.0.0',
          date: '2024-12-28',
          platforms: {
            macos: {
              url: '#coming-soon',
              size: '~150 MB',
              sha256: 'pending',
            },
            linux: {
              url: '#coming-soon',
              size: '~120 MB',
              sha256: 'pending',
            },
          },
          changelog: [
            'Initial release',
            'Offline AI medical assistant',
            'Local LLM integration via Ollama',
            'Encrypted local storage',
          ],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const latestRelease = releases[0];

  return (
    <AppTemplate showChatWidget={false}>
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white dark:from-slate-900 dark:to-slate-800">
        {/* Hero Section */}
        <div className="max-w-6xl mx-auto px-4 py-12">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-slate-900 dark:text-white mb-4">
              Aurity Desktop
            </h1>
            <p className="text-xl text-slate-600 dark:text-slate-300 max-w-2xl mx-auto">
              Medical AI Assistant that runs 100% on your device.
              No cloud. No data sharing. Complete privacy.
            </p>
          </div>

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-6 mb-12">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm border border-slate-200 dark:border-slate-700"
              >
                <feature.icon className="w-8 h-8 text-blue-600 dark:text-blue-400 mb-4" />
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                  {feature.title}
                </h3>
                <p className="text-slate-600 dark:text-slate-300">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>

          {/* Download Cards */}
          {loading ? (
            <div className="flex justify-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-8 mb-12">
              {/* macOS Download */}
              <div className="bg-white dark:bg-slate-800 rounded-xl p-8 shadow-lg border border-slate-200 dark:border-slate-700">
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center">
                    <Apple className="w-10 h-10 text-slate-700 dark:text-slate-300" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                      macOS
                    </h2>
                    <p className="text-slate-500">Apple Silicon & Intel</p>
                  </div>
                </div>

                {latestRelease?.platforms.macos ? (
                  <>
                    <Button
                      className="w-full mb-4 h-12 text-lg"
                      onClick={() => {
                        if (latestRelease.platforms.macos?.url !== '#coming-soon') {
                          window.open(latestRelease.platforms.macos?.url, '_blank');
                        }
                      }}
                      disabled={latestRelease.platforms.macos.url === '#coming-soon'}
                    >
                      <Download className="w-5 h-5 mr-2" />
                      {latestRelease.platforms.macos.url === '#coming-soon'
                        ? 'Coming Soon'
                        : `Download v${latestRelease.version}`}
                    </Button>
                    <div className="text-sm text-slate-500 space-y-1">
                      <p>Size: {latestRelease.platforms.macos.size}</p>
                      <p className="font-mono text-xs truncate">
                        SHA256: {latestRelease.platforms.macos.sha256}
                      </p>
                    </div>
                  </>
                ) : (
                  <p className="text-slate-500">Not available yet</p>
                )}

                <hr className="my-6 border-slate-200 dark:border-slate-700" />

                <h3 className="font-semibold text-slate-900 dark:text-white mb-3">
                  System Requirements
                </h3>
                <ul className="text-sm text-slate-600 dark:text-slate-300 space-y-2">
                  {Object.entries(systemRequirements.macos).map(([key, value]) => (
                    <li key={key} className="flex items-start gap-2">
                      <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                      <span>{value}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Linux Download */}
              <div className="bg-white dark:bg-slate-800 rounded-xl p-8 shadow-lg border border-slate-200 dark:border-slate-700">
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center">
                    <Monitor className="w-10 h-10 text-slate-700 dark:text-slate-300" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                      Linux
                    </h2>
                    <p className="text-slate-500">AppImage (x86_64)</p>
                  </div>
                </div>

                {latestRelease?.platforms.linux ? (
                  <>
                    <Button
                      className="w-full mb-4 h-12 text-lg"
                      onClick={() => {
                        if (latestRelease.platforms.linux?.url !== '#coming-soon') {
                          window.open(latestRelease.platforms.linux?.url, '_blank');
                        }
                      }}
                      disabled={latestRelease.platforms.linux.url === '#coming-soon'}
                    >
                      <Download className="w-5 h-5 mr-2" />
                      {latestRelease.platforms.linux.url === '#coming-soon'
                        ? 'Coming Soon'
                        : `Download v${latestRelease.version}`}
                    </Button>
                    <div className="text-sm text-slate-500 space-y-1">
                      <p>Size: {latestRelease.platforms.linux.size}</p>
                      <p className="font-mono text-xs truncate">
                        SHA256: {latestRelease.platforms.linux.sha256}
                      </p>
                    </div>
                  </>
                ) : (
                  <p className="text-slate-500">Not available yet</p>
                )}

                <hr className="my-6 border-slate-200 dark:border-slate-700" />

                <h3 className="font-semibold text-slate-900 dark:text-white mb-3">
                  System Requirements
                </h3>
                <ul className="text-sm text-slate-600 dark:text-slate-300 space-y-2">
                  {Object.entries(systemRequirements.linux).map(([key, value]) => (
                    <li key={key} className="flex items-start gap-2">
                      <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                      <span>{value}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Changelog */}
          {latestRelease?.changelog && (
            <div className="bg-white dark:bg-slate-800 rounded-xl p-8 shadow-sm border border-slate-200 dark:border-slate-700 mb-12">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4">
                What&apos;s New in v{latestRelease.version}
              </h2>
              <ul className="space-y-2">
                {latestRelease.changelog.map((item, index) => (
                  <li
                    key={index}
                    className="flex items-start gap-2 text-slate-600 dark:text-slate-300"
                  >
                    <CheckCircle className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Installation Instructions */}
          <div className="bg-slate-100 dark:bg-slate-800/50 rounded-xl p-8">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4">
              Installation
            </h2>
            <div className="grid md:grid-cols-2 gap-8">
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
                  <Apple className="w-5 h-5" /> macOS
                </h3>
                <ol className="text-slate-600 dark:text-slate-300 space-y-2 list-decimal list-inside">
                  <li>Download the .dmg file</li>
                  <li>Double-click to open</li>
                  <li>Drag Aurity to Applications</li>
                  <li>First run: Right-click → Open (to bypass Gatekeeper)</li>
                </ol>
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
                  <Monitor className="w-5 h-5" /> Linux
                </h3>
                <ol className="text-slate-600 dark:text-slate-300 space-y-2 list-decimal list-inside">
                  <li>Download the .AppImage file</li>
                  <li>Make executable: <code className="bg-slate-200 dark:bg-slate-700 px-1 rounded">chmod +x Aurity*.AppImage</code></li>
                  <li>Run: <code className="bg-slate-200 dark:bg-slate-700 px-1 rounded">./Aurity*.AppImage</code></li>
                </ol>
              </div>
            </div>

            <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <p className="text-blue-800 dark:text-blue-200 text-sm">
                <strong>Note:</strong> Aurity Desktop requires{' '}
                <a
                  href="https://ollama.ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline inline-flex items-center gap-1"
                >
                  Ollama <ExternalLink className="w-3 h-3" />
                </a>{' '}
                for local AI. Install Ollama first, then run{' '}
                <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">ollama pull qwen3:8b</code>{' '}
                to download a model.
              </p>
            </div>
          </div>
        </div>
      </div>
    </AppTemplate>
  );
}
