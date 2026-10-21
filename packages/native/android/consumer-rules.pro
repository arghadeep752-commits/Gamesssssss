# Applied automatically to apps that use @devdarshan/native when R8 is enabled.

# The Expo module is instantiated from generated autolinking code.
-keep class com.devdarshan.nativemodule.** { *; }

# Credential Manager loads its Google Play services implementation reflectively.
-if class androidx.credentials.CredentialManager
-keep class androidx.credentials.playservices.** { *; }
-keep class com.google.android.libraries.identity.googleid.** { *; }
