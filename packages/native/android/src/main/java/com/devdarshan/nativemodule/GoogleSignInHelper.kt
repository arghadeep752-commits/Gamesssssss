package com.devdarshan.nativemodule

import android.app.Activity
import android.content.Context
import android.os.CancellationSignal
import androidx.core.content.ContextCompat
import androidx.credentials.ClearCredentialStateRequest
import androidx.credentials.CredentialManager
import androidx.credentials.CredentialManagerCallback
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.GetCredentialResponse
import androidx.credentials.exceptions.ClearCredentialException
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialException
import androidx.credentials.exceptions.GetCredentialInterruptedException
import androidx.credentials.exceptions.GetCredentialProviderConfigurationException
import androidx.credentials.exceptions.GetCredentialUnsupportedException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import expo.modules.kotlin.Promise

/**
 * "Sign in with Google" through Android Credential Manager. Returns a Google ID
 * token that the JavaScript layer exchanges for a Firebase session
 * (GoogleAuthProvider.credential + signInWithCredential). No client secret is
 * involved; Google verifies the app by package name + signing certificate SHA-1.
 */
object GoogleSignInHelper {

  fun signIn(activity: Activity, webClientId: String, promise: Promise) {
    if (webClientId.isBlank()) {
      promise.reject(ErrorCodes.SIGNIN_CONFIG, "Google sign-in is not configured for this build (no web client ID)", null)
      return
    }
    val manager = CredentialManager.create(activity)
    val option = GetSignInWithGoogleOption.Builder(webClientId).build()
    val request = GetCredentialRequest.Builder().addCredentialOption(option).build()
    manager.getCredentialAsync(
      activity,
      request,
      CancellationSignal(),
      ContextCompat.getMainExecutor(activity),
      object : CredentialManagerCallback<GetCredentialResponse, GetCredentialException> {
        override fun onResult(result: GetCredentialResponse) {
          handleResult(result, promise)
        }

        override fun onError(e: GetCredentialException) {
          rejectWith(e, promise)
        }
      },
    )
  }

  fun signOut(context: Context, promise: Promise) {
    val manager = CredentialManager.create(context)
    manager.clearCredentialStateAsync(
      ClearCredentialStateRequest(),
      CancellationSignal(),
      ContextCompat.getMainExecutor(context),
      object : CredentialManagerCallback<Void?, ClearCredentialException> {
        override fun onResult(result: Void?) {
          promise.resolve(null)
        }

        override fun onError(e: ClearCredentialException) {
          // Firebase sign-out has already happened; clearing the account chooser state is best effort.
          promise.resolve(null)
        }
      },
    )
  }

  private fun handleResult(result: GetCredentialResponse, promise: Promise) {
    val credential = result.credential
    if (credential is CustomCredential && credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
      try {
        val google = GoogleIdTokenCredential.createFrom(credential.data)
        promise.resolve(
          mapOf(
            "idToken" to google.idToken,
            "email" to google.id,
            "displayName" to google.displayName,
            "photoUrl" to google.profilePictureUri?.toString(),
          ),
        )
      } catch (e: GoogleIdTokenParsingException) {
        promise.reject(ErrorCodes.SIGNIN_FAILED, "Google returned an unreadable sign-in token", e)
      }
    } else {
      promise.reject(ErrorCodes.SIGNIN_FAILED, "Unexpected credential type from Google", null)
    }
  }

  private fun rejectWith(e: GetCredentialException, promise: Promise) {
    val detail = (e.errorMessage?.toString() ?: e.message ?: "").trim()
    val (code, message) = when {
      e is GetCredentialCancellationException -> ErrorCodes.SIGNIN_CANCELLED to "Sign-in was cancelled"
      e is NoCredentialException -> ErrorCodes.SIGNIN_NO_ACCOUNT to "No Google account is available on this phone"
      e is GetCredentialInterruptedException -> ErrorCodes.SIGNIN_INTERRUPTED to "Sign-in was interrupted, please try again"
      e is GetCredentialProviderConfigurationException || e is GetCredentialUnsupportedException ->
        ErrorCodes.SIGNIN_UNSUPPORTED to "Google Play services is missing or needs an update"
      looksLikeConfigurationError(detail) ->
        ErrorCodes.SIGNIN_CONFIG to "This app build is not registered for Google sign-in yet"
      else -> ErrorCodes.SIGNIN_FAILED to "Google sign-in failed"
    }
    val full = if (detail.isNotEmpty() && code != ErrorCodes.SIGNIN_CANCELLED) "$message ($detail)" else message
    promise.reject(code, full, e)
  }

  /** Missing SHA-1 / OAuth client registration surfaces as these Play services errors. */
  private fun looksLikeConfigurationError(detail: String): Boolean =
    CONFIG_ERROR_HINTS.any { detail.contains(it, ignoreCase = true) }

  private val CONFIG_ERROR_HINTS = listOf(
    "28444",
    "developer console is not set up",
    "DEVELOPER_ERROR",
    "[10]",
    "[16]",
    "reauth",
    "not configured",
  )
}
