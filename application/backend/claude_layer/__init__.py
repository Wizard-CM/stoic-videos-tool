"""The Claude layer: Claude Code, run headless through the Claude Agent SDK, designs characters, backgrounds and scripts
and directs every video. Opus leads each task and hands simpler subtasks to Sonnet and Haiku workers.

Import the task modules directly (claude_layer.character, .background, .script, .director); this package file stays
empty so importing one never pulls in the others.
"""
