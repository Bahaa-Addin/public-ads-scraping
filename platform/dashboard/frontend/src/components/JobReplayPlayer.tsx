/**
 * JobReplayPlayer - Screenshot playback player for job replay
 *
 * Provides video-like controls for viewing stored screenshots
 * from completed scraping jobs.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  ChevronLeft,
  ChevronRight,
  Loader,
  AlertCircle,
  Image as ImageIcon,
  Clock,
  ExternalLink
} from 'lucide-react';
import { useJobScreenshots, getScreenshotUrl } from '@/hooks/useJobScreenshots';
import { cn, formatRelativeTime } from '@/lib/utils';

interface JobReplayPlayerProps {
  jobId: string;
  className?: string;
  onClose?: () => void;
}

type PlaybackSpeed = 0.5 | 1 | 2 | 4;

export function JobReplayPlayer({ jobId, className, onClose }: JobReplayPlayerProps) {
  const { data, isLoading, error } = useJobScreenshots(jobId);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<PlaybackSpeed>(1);
  const [showThumbnails, setShowThumbnails] = useState(true);
  const thumbnailsRef = useRef<HTMLDivElement>(null);

  const screenshots = data?.screenshots || [];
  const currentScreenshot = screenshots[currentIndex];

  // Auto-advance when playing
  useEffect(() => {
    if (!isPlaying || screenshots.length === 0) return;

    const baseInterval = 2000; // Base 2 second interval (matches save rate)
    const interval = setInterval(() => {
      setCurrentIndex((i) => {
        if (i >= screenshots.length - 1) {
          setIsPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, baseInterval / playbackSpeed);

    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, screenshots.length]);

  // Scroll thumbnail into view
  useEffect(() => {
    if (thumbnailsRef.current && showThumbnails) {
      const thumbnail = thumbnailsRef.current.children[currentIndex] as HTMLElement;
      if (thumbnail) {
        thumbnail.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
      }
    }
  }, [currentIndex, showThumbnails]);

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case ' ':
          e.preventDefault();
          setIsPlaying((p) => !p);
          break;
        case 'ArrowLeft':
          setCurrentIndex((i) => Math.max(0, i - 1));
          break;
        case 'ArrowRight':
          setCurrentIndex((i) => Math.min(screenshots.length - 1, i + 1));
          break;
        case 'Home':
          setCurrentIndex(0);
          break;
        case 'End':
          setCurrentIndex(screenshots.length - 1);
          break;
        case 'Escape':
          onClose?.();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [screenshots.length, onClose]);

  const goToStart = useCallback(() => {
    setCurrentIndex(0);
    setIsPlaying(false);
  }, []);

  const goToEnd = useCallback(() => {
    setCurrentIndex(screenshots.length - 1);
    setIsPlaying(false);
  }, [screenshots.length]);

  const goBack = useCallback(() => {
    setCurrentIndex((i) => Math.max(0, i - 1));
  }, []);

  const goForward = useCallback(() => {
    setCurrentIndex((i) => Math.min(screenshots.length - 1, i + 1));
  }, [screenshots.length]);

  const togglePlay = useCallback(() => {
    if (currentIndex >= screenshots.length - 1) {
      // If at end, restart from beginning
      setCurrentIndex(0);
    }
    setIsPlaying((p) => !p);
  }, [currentIndex, screenshots.length]);

  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center py-12', className)}>
        <div className="text-center text-surface-500">
          <Loader className="w-8 h-8 mx-auto mb-2 animate-spin" />
          <p>Loading screenshots...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('flex items-center justify-center py-12', className)}>
        <div className="text-center text-danger-400">
          <AlertCircle className="w-8 h-8 mx-auto mb-2" />
          <p>Failed to load screenshots</p>
          <p className="text-xs text-surface-500 mt-1">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      </div>
    );
  }

  if (screenshots.length === 0) {
    return (
      <div className={cn('flex items-center justify-center py-12', className)}>
        <div className="text-center text-surface-500">
          <ImageIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-lg font-medium mb-1">No Screenshots Available</p>
          <p className="text-sm">This job doesn't have any recorded screenshots.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col bg-surface-900 rounded-lg overflow-hidden', className)}>
      {/* Video Display */}
      <div className="relative flex-1 bg-black flex items-center justify-center min-h-[400px]">
        {currentScreenshot && (
          <img
            src={getScreenshotUrl(jobId, currentScreenshot.filename)}
            alt={`Screenshot ${currentIndex + 1}`}
            className="max-w-full max-h-full object-contain"
          />
        )}

        {/* Overlay with metadata */}
        <div className="absolute top-0 left-0 right-0 p-3 bg-gradient-to-b from-black/70 to-transparent">
          <div className="flex items-center justify-between">
            <div className="text-white">
              <h3 className="font-medium">Job Replay</h3>
              <p className="text-xs text-surface-300">
                {currentIndex + 1} / {screenshots.length} screenshots
              </p>
            </div>
            {currentScreenshot?.timestamp && (
              <div className="flex items-center gap-1 text-xs text-surface-300">
                <Clock className="w-3 h-3" />
                {formatRelativeTime(currentScreenshot.timestamp)}
              </div>
            )}
          </div>
        </div>

        {/* Bottom overlay with URL */}
        {currentScreenshot?.page_url && (
          <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/70 to-transparent">
            <div className="flex items-center gap-2 text-xs text-surface-300">
              <ExternalLink className="w-3 h-3 flex-shrink-0" />
              <span className="truncate">{currentScreenshot.page_url}</span>
            </div>
            {currentScreenshot.action && (
              <p className="text-xs text-surface-400 mt-1">Action: {currentScreenshot.action}</p>
            )}
          </div>
        )}
      </div>

      {/* Progress Bar / Scrubber */}
      <div className="px-4 py-2 bg-surface-850">
        <input
          type="range"
          min={0}
          max={screenshots.length - 1}
          value={currentIndex}
          onChange={(e) => {
            setCurrentIndex(parseInt(e.target.value));
            setIsPlaying(false);
          }}
          className="w-full h-1.5 bg-surface-700 rounded-lg appearance-none cursor-pointer
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:w-3
            [&::-webkit-slider-thumb]:h-3
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:bg-brand-500
            [&::-webkit-slider-thumb]:cursor-pointer
            [&::-webkit-slider-thumb]:hover:bg-brand-400"
        />
      </div>

      {/* Playback Controls */}
      <div className="flex items-center justify-between px-4 py-3 bg-surface-850 border-t border-surface-700">
        <div className="flex items-center gap-1">
          <button
            onClick={goToStart}
            className="p-2 rounded-lg hover:bg-surface-700 transition-colors"
            title="Go to start (Home)"
          >
            <SkipBack className="w-4 h-4 text-surface-300" />
          </button>
          <button
            onClick={goBack}
            className="p-2 rounded-lg hover:bg-surface-700 transition-colors"
            title="Previous (←)"
          >
            <ChevronLeft className="w-5 h-5 text-surface-300" />
          </button>
          <button
            onClick={togglePlay}
            className="p-3 rounded-lg bg-brand-500 hover:bg-brand-600 transition-colors"
            title="Play/Pause (Space)"
          >
            {isPlaying ? (
              <Pause className="w-5 h-5 text-white" />
            ) : (
              <Play className="w-5 h-5 text-white" />
            )}
          </button>
          <button
            onClick={goForward}
            className="p-2 rounded-lg hover:bg-surface-700 transition-colors"
            title="Next (→)"
          >
            <ChevronRight className="w-5 h-5 text-surface-300" />
          </button>
          <button
            onClick={goToEnd}
            className="p-2 rounded-lg hover:bg-surface-700 transition-colors"
            title="Go to end (End)"
          >
            <SkipForward className="w-4 h-4 text-surface-300" />
          </button>
        </div>

        <div className="flex items-center gap-4">
          {/* Speed selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-surface-400">Speed:</span>
            <select
              value={playbackSpeed}
              onChange={(e) => setPlaybackSpeed(parseFloat(e.target.value) as PlaybackSpeed)}
              className="bg-surface-700 text-white text-sm rounded px-2 py-1 border border-surface-600"
            >
              <option value={0.5}>0.5x</option>
              <option value={1}>1x</option>
              <option value={2}>2x</option>
              <option value={4}>4x</option>
            </select>
          </div>

          {/* Thumbnail toggle */}
          <button
            onClick={() => setShowThumbnails(!showThumbnails)}
            className={cn(
              'text-xs px-2 py-1 rounded transition-colors',
              showThumbnails
                ? 'bg-brand-500/20 text-brand-400'
                : 'bg-surface-700 text-surface-400 hover:text-surface-300'
            )}
          >
            Thumbnails
          </button>

          {/* Frame counter */}
          <span className="text-sm text-surface-400 font-mono">
            {String(currentIndex + 1).padStart(3, '0')} / {screenshots.length}
          </span>
        </div>
      </div>

      {/* Thumbnail Strip */}
      {showThumbnails && (
        <div
          ref={thumbnailsRef}
          className="flex gap-1 p-2 bg-surface-900 border-t border-surface-700 overflow-x-auto"
        >
          {screenshots.map((screenshot, index) => (
            <button
              key={screenshot.filename}
              onClick={() => {
                setCurrentIndex(index);
                setIsPlaying(false);
              }}
              className={cn(
                'flex-shrink-0 w-16 h-10 rounded overflow-hidden border-2 transition-all',
                index === currentIndex
                  ? 'border-brand-500 ring-1 ring-brand-500/50'
                  : 'border-transparent opacity-60 hover:opacity-100'
              )}
            >
              <img
                src={getScreenshotUrl(jobId, screenshot.filename)}
                alt={`Thumbnail ${index + 1}`}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default JobReplayPlayer;
