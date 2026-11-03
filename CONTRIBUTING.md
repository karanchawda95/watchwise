# 🤝 Contributing to WatchWise

We welcome contributions to make WatchWise the safest, most comprehensive ADB toolkit for Wear OS!

## 🧪 Development Setup & Testing

Before submitting any changes, ensure all tests pass. WatchWise uses `pytest` with mocked ADB responses to guarantee that tests never accidentally modify the developer's connected devices.

1. **Install testing dependencies:**
   ```powershell
   pip install pytest
   ```
2. **Run the test suite:**
   ```powershell
   python -m pytest
   ```

## 📝 Creating Device Profiles

Profiles map specific watch models to safe actions. When creating or modifying a profile (`schemas/device-profile.schema.json`):

*   **Validation:** Profiles must adhere strictly to the provided JSON schema.
*   **Evidence Level:** You must identify the `evidence_level` (`user-reported` vs `independently-validated`).
*   **Protected Packages:** Always list protected OEM packages (`com.samsung...`, `com.google...`).
*   **Empty Defaults:** Leave unvalidated package rules empty. Do not guess what is safe to disable.

## 🚫 What We Don't Accept

To maintain our safety guarantee, **we will reject Pull Requests that:**
* Add automatic `uninstall` capabilities (we only use `disable-user`).
* Bypass the `--execute --yes` safety gates.
* Execute commands directly against a device in unit tests (always mock the `Adb` class).