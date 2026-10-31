# Compatibility and verification

| Environment | Status |
| --- | --- |
| Ubuntu 26.04, GNOME Shell 50, Wayland | Runtime and menu tested on development machine |
| Isolated GNOME 50 Wayland desktop | Menu rendering and direct Kill callback tested with disposable app |
| Other Linux distributions with GNOME 50 | Installer accepts; not runtime-tested |
| GNOME 49 and earlier / future major versions | Installer rejects; no compatibility claim |
| KDE, Cinnamon, XFCE, other desktops | Unsupported; require separate panel integrations |

The extension is JavaScript plus Python, with no architecture-specific compiled payload. That does not establish runtime compatibility with every architecture or distro.

The reference machine exposes Intel `coretemp` CPU limits at 100°C and an NVMe maximum around 85°C. Limits are read afresh from the driver, never hard-coded to that machine. This release recognizes coretemp, nvme, xe, i915, and amdgpu sensor groups. AMD CPU `k10temp` and NVIDIA proprietary telemetry are not implemented. Sensors without plausible limits are omitted. Missing sensor data must not be interpreted as safe temperatures.

## Why GNOME only

GNOME extensions run inside GNOME Shell and declare compatible shell versions in metadata. A zip or AppImage does not make those APIs available on other desktop environments. Cross-desktop support requires separate implementations and verification.

## Sources consulted

- [GNOME extension anatomy and ZIP distribution](https://gjs.guide/extensions/overview/anatomy.html)
- [GNOME extension review guidelines](https://gjs.guide/extensions/review-guidelines/review-guidelines.html)
- [GNOME extension API and shell-version field](https://gjs.guide/extensions/topics/extension.html)
- [Linux coretemp: model-dependent maximum junction temperature](https://docs.kernel.org/hwmon/coretemp.html)
- [GitHub Releases for downloadable software](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)

This repository is distributed through GitHub. It has not been submitted to or approved by extensions.gnome.org. A helper subprocess is launched per sample; that design and the immediate Kill feature warrant explicit review before any store submission.
