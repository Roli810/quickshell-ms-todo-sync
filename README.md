Quickshell Microsoft To Do Sync

Sync the Quickshell / Illogical-Impulse sidebar todo widget with Microsoft To Do.

This tool keeps the Quickshell sidebar tasks synchronized with a Microsoft To Do list without using Microsoft Graph, Azure, or any API setup.

Instead, it uses a logged-in browser session to read and update tasks.

What It Does

Quickshell stores its sidebar tasks locally in:

~/.local/state/quickshell/user/todo.json

This tool synchronizes that file with Microsoft To Do.

The sync process

Reads tasks from a selected Microsoft To Do list

Updates the local Quickshell todo file

Applies local changes back to Microsoft To Do

Result:

Quickshell sidebar  ⇄  Microsoft To Do
Why This Exists

Using the official Microsoft To Do API normally requires:

Azure / Entra application registration

Microsoft Graph configuration

OAuth token handling

For a simple personal desktop setup this is often overkill.

This project avoids all of that by using:

Playwright UI automation

your existing logged-in session

No API configuration required.

Tested Environment

Developed and tested with:

Arch Linux

Hyprland

Quickshell

Illogical-Impulse dotfiles

It should also work on most Linux systems that support:

Python

Playwright

systemd user services

Features

Bidirectional sync

No Microsoft API setup required

Works with existing Microsoft login session

Integrates with the existing Quickshell todo widget

Runs completely in the background

Optional systemd timer for automatic syncing

How It Works

The Quickshell widget reads tasks from:

~/.local/state/quickshell/user/todo.json

Example task format:

{
  "content": "task text",
  "done": false
}
Sync process

Open Microsoft To Do

Navigate to the selected list

Read task titles and completion state

Compare with the local file

Apply changes both ways

Update the local JSON file

Running in the Background

The recommended setup uses a systemd user timer.

This runs the sync automatically about every 30 seconds.

Advantages:

No terminal required

No visible browser window

Automatic background syncing

First Time Setup

The first run opens a browser window.

Steps:

Sign in to Microsoft To Do

Open the desired task list

Confirm setup

After that the script can run headless in the background.

Limitations

Because this relies on the Microsoft To Do web interface:

UI changes from Microsoft may break selectors

Duplicate task titles are not supported

This is not an official Microsoft integration

For personal desktop use it has proven reliable.

Security

This tool does not store passwords.

Authentication relies on the browser session stored in the Playwright profile.

No Microsoft credentials are embedded in the script.

Disclaimer

This project is not affiliated with Microsoft.
