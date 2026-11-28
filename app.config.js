// Uses the CI build number as Android versionCode, so every build can be uploaded to
// Google Play (each upload needs a higher number). Everything else comes from app.json.
module.exports = ({ config }) => ({
  ...config,
  android: {
    ...config.android,
    versionCode: Number(process.env.VERSION_CODE) || config.android.versionCode,
  },
});
