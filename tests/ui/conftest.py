import os

# Qt widgets in tests are drawn off-screen: no windows flash up on the developer's desktop.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
