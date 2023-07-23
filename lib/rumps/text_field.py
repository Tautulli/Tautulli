from AppKit import NSApplication, NSTextField, NSSecureTextField, NSKeyDown, NSCommandKeyMask


class Editing(NSTextField):
    """NSTextField with cut, copy, paste, undo and selectAll"""
    def performKeyEquivalent_(self, event):
        return _perform_key_equivalent(self, event)


class SecureEditing(NSSecureTextField):
    """NSSecureTextField with cut, copy, paste, undo and selectAll"""
    def performKeyEquivalent_(self, event):
        return _perform_key_equivalent(self, event)


def _perform_key_equivalent(self, event):
    if event.type() == NSKeyDown and event.modifierFlags() & NSCommandKeyMask:
        if event.charactersIgnoringModifiers() == "x":
            NSApplication.sharedApplication().sendAction_to_from_("cut:", None, self)
            return True
        elif event.charactersIgnoringModifiers() == "c":
            NSApplication.sharedApplication().sendAction_to_from_("copy:", None, self)
            return True
        elif event.charactersIgnoringModifiers() == "v":
            NSApplication.sharedApplication().sendAction_to_from_("paste:", None, self)
            return True
        elif event.charactersIgnoringModifiers() == "z":
            NSApplication.sharedApplication().sendAction_to_from_("undo:", None, self)
            return True
        elif event.charactersIgnoringModifiers() == "a":
            NSApplication.sharedApplication().sendAction_to_from_("selectAll:", None, self)
            return True
