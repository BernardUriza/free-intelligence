# 🔊 Text-to-Speech Privacy Policy

## Overview

FI-Stride uses advanced Text-to-Speech (TTS) technology to provide audio guidance during training sessions. This document explains how we handle your voice data and privacy.

---

## 🛡️ Privacy First: Local Processing

By default, **FI-Stride uses locally-hosted TTS engines that process audio entirely on your device**:

### ✅ Local-First Engines (No Cloud Storage)

1. **Kokoro WASM** (Primary)
   - Runs 100% in your browser
   - Uses Web Assembly (WASM) technology
   - ~300MB model downloaded once
   - Zero data sent to external servers
   - Cached in your browser's IndexedDB

2. **Piper ONNX** (Fallback)
   - Open-source neural TTS
   - Runs locally via ONNX Runtime
   - ~100MB per language variant
   - No external API calls
   - Complete privacy guarantee

3. **Web Speech API** (Fallback)
   - Browser-native speech synthesis
   - No downloads required
   - Generated audio never leaves your device
   - Instant fallback if other engines unavailable

---

## ☁️ Cloud TTS (Optional)

If enabled in settings, FI-Stride can optionally use **Azure Text-to-Speech** for premium audio quality. This is **always opt-in** and completely voluntary.

### When Using Azure TTS:

- Your **text input only** is sent to Azure servers
- Returned audio is **streamed directly to your device**
- Audio is **not logged or stored** on Azure servers
- Session ID (your private training context) is **never shared**
- You control this setting: `VITE_USE_CLOUD_TTS` environment variable

### Azure Privacy Terms:
- [Azure Cognitive Services Privacy](https://privacy.microsoft.com/en-us/privacystatement)
- Data processed under your Azure subscription
- Complies with GDPR, CCPA, and regional regulations

---

## 🔐 Data Security

All TTS operations in FI-Stride are protected:

### Encryption
- Session segments use **AES-GCM-256 encryption**
- Each rep/check-in encrypted with unique keys
- Encrypted data stored in **S3** (AWS)
- Private key wrapping via RSA (NAS-hosted)

### Offline-First
- Works without internet connection
- Local audio processing always available
- Sync happens when connected
- Exponential backoff for failed uploads

### No Tracking
- **No analytics** on voice usage
- **No audio recordings** stored
- **No behavioral tracking**
- Only metadata: timestamp, reps completed, RPE level

---

## 👤 Your Voice Data Rights

You have full control:

| Action | Local | Cloud |
|--------|-------|-------|
| **View data** | ✅ IndexedDB browser storage | ✅ Your Azure account |
| **Delete data** | ✅ Clear browser storage | ✅ Azure compliance portal |
| **Export data** | ✅ Export to JSON | ✅ Azure export tools |
| **Disable TTS** | ✅ Use visual guidance instead | ✅ Disable cloud TTS |

### How to Delete Local Audio:
1. Open Browser DevTools (F12)
2. Application → IndexedDB → fi-stride-offline
3. Right-click → Delete

---

## 🎙️ Voice Selection

FI-Stride uses a feminine voice (KATNISS coach) for consistency and accessibility:

- **Language**: Spanish (es-ES) or English (en-US)
- **Voice**: Azure Cognitive Services "nova" voice (female)
- **Speed**: 0.85x normal (optimized for comprehension)
- **Pitch**: Standard (1.0)

---

## 📋 Compliance

FI-Stride TTS features comply with:

- ✅ **GDPR** (EU - General Data Protection Regulation)
- ✅ **CCPA** (CA - California Consumer Privacy Act)
- ✅ **HIPAA** (if used in medical context - opt-in)
- ✅ **WCAG 2.1** (Web Content Accessibility Guidelines)
- ✅ **Down Syndrome Accessibility Standards** (T21)

---

## ❓ Frequently Asked Questions

**Q: Is my voice recorded?**
A: No. FI-Stride generates speech from text, not recordings.

**Q: Where is the audio data stored?**
A: On your device locally, or in your Azure account if cloud TTS is enabled.

**Q: Can I use FI-Stride offline?**
A: Yes! All local TTS engines work without internet.

**Q: How do I disable cloud TTS?**
A: Set `VITE_USE_CLOUD_TTS=false` in `.env.local` (default).

**Q: Is my training data private?**
A: Yes. Session metadata is encrypted before uploading. No coach or admin can see audio.

**Q: Can I export my training history?**
A: Yes. Use the Export button in the dashboard to get JSON/CSV.

---

## 📞 Contact & Support

Questions about privacy?

- **Privacy Officer**: Contact Free Intelligence support
- **Data Requests**: support@free-intelligence.ai
- **Report Issue**: GitHub Issues or support portal

---

## 📅 Last Updated

**November 6, 2025**

This policy is reviewed monthly and updated as needed. Check back regularly for changes.

---

## 🔗 Related Documents

- [Main Privacy Policy](/)
- [Terms of Service](/terms)
- [Accessibility Statement](/)
- [Data Retention Policy](/)
