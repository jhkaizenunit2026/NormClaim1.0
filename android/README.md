# NormClaim Android client

Open the `android/` folder in **Android Studio** (Hedgehog+). Use **JDK 17**.

- **Emulator:** `BuildConfig.BASE_URL` defaults to `http://10.0.2.2:8000/` (already set in `app/build.gradle`).
- **Physical device:** change `buildConfigField` in `app/build.gradle` to `http://<your-lan-ip>:8000/` and ensure the phone can reach the machine running FastAPI.

Flow: **MainActivity** lists documents → FAB opens **UploadActivity** (pick PDF → upload → extract → reconcile) → **ResultActivity** (Entities / Claim Report tabs). Tapping a document opens **ResultActivity** using GET endpoints.

If Gradle wrapper files are missing, run from `android/`: `gradle wrapper` (once) or use Android Studio’s “Gradle” tooling to generate them.
