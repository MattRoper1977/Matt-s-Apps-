# Deployment guide

## Supported deployment patterns

### 1. Extract-and-open

Copy the complete release ZIP to the device, extract it and open `index.html`. This is the simplest fully offline route.

### 2. Shared network folder

Place the extracted folder on a read-only staff or curriculum share. Learners may open the HTML files in a supported browser and export project records to an approved personal or class location. Test browser download permissions before the session.

### 3. Static web hosting

The folder can be served from any ordinary static host because it contains only HTML, JSON, Markdown and images. Preserve relative paths. No server-side code, database, build command or environment variable is required.

For public hosting, review local safeguarding, privacy and content-governance requirements first. The applications themselves do not upload evidence, but users can still export files to their device.

## Pre-session deployment check

1. Extract the complete folder.
2. Run `RELEASE_SELF_CHECK.html` against the extracted folder.
3. Open `index.html` in the intended browser.
4. Open one specialist studio and its Professional Studio Record.
5. Test one `.makerlab` export and re-import.
6. Test any required printing at actual size, including the 50 mm calibration bar.
7. Test local image permissions where a physical-photo comparator will be used.
8. Confirm shared-resource and physical-process controls separately.

## Browser and device notes

The suite uses standard Canvas, SVG, File, Blob, localStorage, crypto digest and postMessage APIs. A current Chromium-, Firefox- or WebKit-based browser is recommended. Printing, download locations, file-picker behaviour and `file://` local storage differ between managed environments, so exported records should be treated as the reliable record.

For Chromebooks or locked-down devices, confirm that:

- local HTML files can open;
- downloads are allowed;
- image files can be selected where needed;
- pop-up blocking does not prevent printable dossier windows;
- the device can print at 100% rather than “fit to page”.

## Folder integrity

Do not separate the control rooms from the eight app files. The shell and directors use relative filenames. Renaming an app file will break launch and relay routes unless the catalogue and relevant embedded lists are also updated.

`RELEASE_SELF_CHECK.html` verifies the release files against embedded SHA-256 values. It reports altered, missing and unexpected files. The checker itself and generated project evidence are outside its protected file set.

## Classroom operation

- `STUDIO_DIRECTOR.html` is a compatibility route for older bookmarks; it sends staff to the three current control rooms.
- Use `TEACHER_STUDIO_DIRECTOR.html` for groups, resource constraints, rotations, station cards and live workshop pulse.
- Use `STUDIO_SHELL.html` when one learner or group will travel between connected representations.
- Use `PORTFOLIO_MODERATION_HUB.html` after project files have been exported.
- Use a specialist app directly for a single-station lesson or when embedded iframes are restricted.

## Back-up and transfer

Export `.makerlab` records at natural checkpoints, especially before changing device or browser profile. For a multi-station project, also export `.makerstudio`. Retain an untouched original and a working copy where records will be reviewed or merged.

## Update and rollback

Keep the release ZIP and its checksum files. Deploy a new version into a new folder rather than overwriting the previous release. Project formats may evolve; retaining the producing version supports audit and reopening.

## Troubleshooting

- **A page opens but saved work is absent:** import the last exported project; local browser storage may be isolated by folder or browser profile.
- **A direct relay is unavailable:** use the Studio Shell, ensure both source and target have been opened in the session, or export/import the relevant project records manually.
- **A print pattern is incorrectly scaled:** disable “fit”, print at 100%, and measure the 50 mm calibration bar before transferring to material.
- **A file will not import:** confirm it was created by the correct PRO v2 tool and has not been renamed with a misleading extension.
- **Managed browser blocks the shell iframe:** open the specialist studio directly; project export/import remains available.
