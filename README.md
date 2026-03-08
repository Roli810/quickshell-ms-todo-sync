Quickshell Microsoft To Do Sync

Sync the Quickshell / Illogical-Impulse sidebar todo widget with Microsoft To Do.

This tool keeps the Quickshell sidebar tasks synchronized with a Microsoft To Do list without using Microsoft Graph, Azure, or any API setup.

Instead, it uses a logged-in browser session to read and update tasks.

What It Does

Quickshell stores its sidebar tasks locally in:

~/.local/state/quickshell/user/todo.json

This tool syncs that file with Microsoft To Do.

It will:

• read tasks from a selected Microsoft To Do list
• update the local Quickshell todo file
• apply local changes back to Microsoft To Do

Result: bidirectional sync

Quickshell sidebar  ⇄  Microsoft To Do
Why This Exists

Using the official Microsoft To Do API requires:

Azure / Entra app registration

Microsoft Graph setup

OAuth configuration

For a personal desktop setup this is often unnecessary.

This tool avoids all of that by using Playwright UI automation with your existing logged-in session.

No API configuration required.

Tested Environment

Developed and tested with:

Arch Linux

Hyprland

Quickshell

Illogical-Impulse dotfiles

It should also work on most Linux systems with:

Python

Playwright

systemd

Features

• bidirectional sync
• no Microsoft API setup required
• works with existing Microsoft login session
• integrates with the existing Quickshell todo widget
• runs completely in the background
• optional systemd timer for automatic syncing

How It Works

The Quickshell widget reads tasks from:

~/.local/state/quickshell/user/todo.json

Each task looks like:

{
  "content": "task text",
  "done": false
}

The sync tool:

opens Microsoft To Do

loads the selected list

reads task titles and completion state

compares them with the local file

applies any changes both ways

updates the local JSON file

Running in the Background

The recommended setup uses a systemd user timer.

This runs the sync automatically every ~30 seconds.

Advantages:

• no terminal needed
• no visible browser window
• automatic syncing in the background

First Time Setup

The first run opens a browser window.

You simply:

sign in to Microsoft To Do

open the desired list

confirm setup

After that the script can run headless in the background.

Limitations

Because this relies on the Microsoft To Do web UI:

• UI changes from Microsoft could break selectors
• duplicate task titles are not supported
• this is not an official Microsoft integration

Security

This tool does not store passwords.

Authentication relies on the browser session stored in the Playwright profile.

No Microsoft credentials are embedded in the script.
