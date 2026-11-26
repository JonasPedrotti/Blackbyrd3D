# Privacy

Blackbyrd3D has no telemetry, analytics, crash reporting or licence check,
and it never uploads your model files. It connects to other systems only in
the cases below, and apart from the update check, only when you ask it to.

**Update check (on by default).** Each time the app starts, it asks the GitHub
Releases API (`api.github.com`) whether a newer version exists. The request
carries nothing about you or your work beyond what any HTTPS request reveals:
your IP address and the user agent `Blackbyrd3D-update-check`. The Windows
installer explains this and lets you turn it off before anything is installed.
To turn it off at any time:

- clear *Check GitHub for updates on startup* in the installer, or
  **Settings ▸ Updates** in the app;
- or set `check_updates` to `false` in `~/.config/blackbyrd3d/settings.json`
  (`%USERPROFILE%\.config\blackbyrd3d\settings.json` on Windows);
- or start the app with `BYRD3D_NO_UPDATE_CHECK=1` in the environment.

**Help ▸ Check for Updates** and **Check Now** in Settings ask GitHub when you
press them, whatever the setting. *Update now* (the Windows installer and an
AppImage) downloads the new release from github.com with the user agent
`Blackbyrd3D-updater`, checks it against the SHA256 GitHub lists for it, and
installs it. Elsewhere *Download* and *Release Notes* open GitHub in your
browser. See the
[GitHub General Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement).

**AI assistant (off until you set it up).** The assistant sends nothing until
you choose a provider, give it what it needs, and press Send. Then it sends
your prompt, the conversation so far, the names of selected objects, a
description of the scene (object names, kinds, layers, bounding boxes and any
text in the model), the output of commands it runs, and a viewport screenshot
when the model asks for one. It goes to the provider you picked:

- Anthropic (`api.anthropic.com`), with your API key:
  [Anthropic privacy policy](https://www.anthropic.com/legal/privacy)
- OpenAI (`api.openai.com`), with your API key:
  [OpenAI privacy policy](https://openai.com/policies/privacy-policy/)
- a ChatGPT account, through the Codex command-line tool that you install and
  sign in to yourself. Codex talks to OpenAI under OpenAI's terms. Once an
  account is connected, Blackbyrd3D starts Codex when it opens with the
  Assistant pane showing.
- a local or custom server you name (LM Studio at `127.0.0.1:1234` by
  default), under whatever terms that server has.

Listing a provider's models happens only when you ask for the list. API keys
are read from `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`, or stored in plain text
in `settings.json` if you enter them in the app.

**Local connections.** So that scripts and assistants you run yourself can
drive it, the app listens on `127.0.0.1` (this computer only), on a port
between 5757 and 5776. Other computers cannot reach it. Set `BYRD3D_NO_RPC=1`
to turn it off.

**Plugins.** Plugins you install run with your permissions and can do anything
a program can, including using the network. This policy covers Blackbyrd3D
itself, not plugins.

## Uninstalling

On Windows, use **Settings ▸ Apps ▸ Installed apps**, or the uninstaller in the
installation folder. It removes everything the installer put there. It leaves
your own files: models you saved, and these folders in your home folder
(`%USERPROFILE%` on Windows), which you can delete:

- `.config/blackbyrd3d`: settings and any API keys you entered
- `.blackbyrd3d`: plugins, the crash log and the local connection port
- `.local/share/blackbyrd3d`: autosaves and session journals

## Reporting a problem

If you believe Blackbyrd3D breaks this policy, please
[open an issue](https://github.com/JonasPedrotti/Blackbyrd3D/issues).
