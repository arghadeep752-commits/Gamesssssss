import type { Wallpaper } from '@devdarshan/shared';
import { Badge, type BadgeTone } from '@devdarshan/ui';

export function wallpaperState(w: Pick<Wallpaper, 'status' | 'processing'>): { label: string; tone: BadgeTone } {
  if (w.status === 'deleting') return { label: 'Deleting', tone: 'danger' };
  if (w.processing === 'failed') return { label: w.status === 'published' ? 'Live · update failed' : 'Failed', tone: 'danger' };
  if (w.processing === 'uploading') return { label: 'Uploading', tone: 'warning' };
  if (w.processing === 'processing') return { label: 'Processing', tone: 'warning' };
  if (w.status === 'published') return { label: 'Published', tone: 'success' };
  return { label: 'Draft', tone: 'neutral' };
}

export function StatusBadge({ wallpaper }: { wallpaper: Pick<Wallpaper, 'status' | 'processing'> }) {
  const state = wallpaperState(wallpaper);
  return <Badge label={state.label} tone={state.tone} />;
}
