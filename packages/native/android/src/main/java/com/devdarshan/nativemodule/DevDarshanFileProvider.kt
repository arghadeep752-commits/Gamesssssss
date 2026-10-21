package com.devdarshan.nativemodule

import androidx.core.content.FileProvider

/**
 * A dedicated FileProvider subclass so its manifest entry never clashes with other
 * libraries that also declare androidx.core.content.FileProvider.
 */
class DevDarshanFileProvider : FileProvider()
