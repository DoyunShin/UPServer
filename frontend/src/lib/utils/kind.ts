export type FileKind = 'pdf' | 'image' | 'audio' | 'video' | 'text' | 'archive' | 'file';

const TEXT_EXTS = new Set([
  'txt',
  'md',
  'markdown',
  'json',
  'js',
  'mjs',
  'cjs',
  'ts',
  'jsx',
  'tsx',
  'py',
  'go',
  'rs',
  'css',
  'scss',
  'html',
  'htm',
  'xml',
  'yml',
  'yaml',
  'sh',
  'bash',
  'zsh',
  'c',
  'h',
  'cpp',
  'hpp',
  'java',
  'rb',
  'php',
  'sql',
  'toml',
  'ini',
  'conf',
  'log',
  'csv',
  'tsv',
  'svelte',
  'vue'
]);

const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'avif', 'svg', 'bmp', 'ico']);
const AUDIO_EXTS = new Set(['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'opus']);
const VIDEO_EXTS = new Set(['mp4', 'webm', 'mov', 'mkv', 'avi', 'm4v']);
const ARCHIVE_EXTS = new Set(['zip', 'tar', 'gz', 'tgz', '7z', 'rar', 'bz2', 'xz']);

export function extOf(filename: string): string {
  const i = filename.lastIndexOf('.');
  if (i < 0 || i === filename.length - 1) return '';
  return filename.slice(i + 1).toLowerCase();
}

export function kindFromName(filename: string, mimeType?: string): FileKind {
  const ext = extOf(filename);
  if (ext === 'pdf') return 'pdf';
  if (IMAGE_EXTS.has(ext)) return 'image';
  if (AUDIO_EXTS.has(ext)) return 'audio';
  if (VIDEO_EXTS.has(ext)) return 'video';
  if (TEXT_EXTS.has(ext)) return 'text';
  if (ARCHIVE_EXTS.has(ext)) return 'archive';

  if (mimeType) {
    if (mimeType === 'application/pdf') return 'pdf';
    if (mimeType.startsWith('image/')) return 'image';
    if (mimeType.startsWith('audio/')) return 'audio';
    if (mimeType.startsWith('video/')) return 'video';
    if (mimeType.startsWith('text/') || mimeType === 'application/json') return 'text';
    if (
      mimeType === 'application/zip' ||
      mimeType === 'application/x-tar' ||
      mimeType === 'application/gzip' ||
      mimeType === 'application/x-7z-compressed' ||
      mimeType === 'application/x-rar-compressed'
    ) {
      return 'archive';
    }
  }

  return 'file';
}

export const ICONS: Record<FileKind, string> = {
  pdf: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
  image:
    '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
  audio: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  video:
    '<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>',
  text: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
  archive: '<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="3" x2="12" y2="21"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>'
};
