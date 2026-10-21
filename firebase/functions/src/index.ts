import { setGlobalOptions } from 'firebase-functions/v2';

// Caps runaway scaling (and cost) for every function unless it sets its own limit.
setGlobalOptions({ maxInstances: 10 });

export { processUpload } from './triggers/storage';
export { onWallpaperWritten, onAppConfigWritten, onFavoriteWritten, onCategoryWritten } from './triggers/firestore';
export { bootstrapAdmin, setAdminRole } from './callables/admins';
export { deleteWallpaper, retryWallpaperProcessing, recordDownload } from './callables/wallpapers';
export { deleteCategory, seedStarterCategories } from './callables/categories';
export { deleteMyAccount } from './callables/account';
export { cleanupStaleUploads } from './scheduled/cleanup';
