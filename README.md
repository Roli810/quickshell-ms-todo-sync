Quickshell Microsoft To Do Sync

A small utility that synchronizes the Quickshell / Illogical-Impulse sidebar todo widget with Microsoft To Do.

It allows the Quickshell todo sidebar to stay in sync with a real Microsoft To Do list without using the Microsoft Graph API or Azure configuration.

The tool works by reading and writing the same JSON file that the Quickshell widget already uses.

What This Does

The Quickshell todo widget stores its tasks locally in a JSON file.

Example location:

~/.local/state/quickshell/user/todo.json

This tool:

Opens Microsoft To Do using a persistent browser session.

Reads tasks from a specific list.

Synchronizes them with the local Quickshell todo file.

Applies local changes back to Microsoft To Do.

The result is bidirectional sync between:

Microsoft To Do

the Quickshell sidebar widget

Why This Exists

The official Microsoft To Do API requires:

Azure / Entra application registration

Microsoft Graph configuration

OAuth tokens

For simple personal desktop setups this is unnecessarily complex.

This tool instead uses UI automation through Playwright, allowing synchronization using your already logged-in browser session.

No API setup is required.

Supported Environment

The tool was developed and tested on:

Arch Linux

Hyprland

Quickshell

Illogical-Impulse dotfiles

It should work on most Linux systems that support:

Python

Playwright

systemd user services

Features

Bidirectional sync

Works with existing Microsoft login session

No Azure or Microsoft Graph configuration

Works with the existing Quickshell todo widget

Can run completely in the background

Optional systemd timer for automatic syncing

How It Works

The Quickshell widget reads tasks from:

~/.local/state/quickshell/user/todo.json

Each task looks like this:

{
  "content": "task text",
  "done": false
}

This tool:

Opens Microsoft To Do

Navigates to the selected list

Scrapes task titles and completion states

Compares them with the local file

Applies any changes on both sides

Updates the local JSON file

Background Sync

The recommended setup is a systemd user timer.

This allows the sync to run automatically in the background without any visible window.

Typical setup:

service runs the sync script

timer runs it every ~30 seconds

This provides near-real-time synchronization between Microsoft To Do and Quickshell.

First Time Setup

The first run requires opening a browser window so the script can use a persistent login session.

You simply:

sign in to Microsoft To Do

open the desired task list

confirm the setup

After this step, synchronization can run headless in the background.

Configuration

The tool uses a small JSON configuration file where you define:

the Microsoft To Do list name

the location of the Quickshell todo file

where the Playwright browser profile is stored

whether the browser runs headless

whether task deletions should sync

Once configured, the script runs automatically without user interaction.

Limitations

Because this tool relies on the Microsoft To Do web interface:

Changes to the Microsoft To Do website may break selectors

Duplicate task titles are not supported

This is not an official Microsoft integration

However, for personal desktop setups it has proven reliable.

Security

This tool does not store passwords.

Authentication relies on the existing browser session stored in the Playwright profile.

No Microsoft credentials are ever embedded in the script.
