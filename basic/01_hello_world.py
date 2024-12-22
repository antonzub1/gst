import sys

import gi

gi.require_versions({"GLib": "2.0", "GObject": "2.0", "Gst": "1.0"})

from gi.repository import Gst, GObject, GLib

pipeline = None
bus = None
message = None

Gst.init(sys.argv[1:])

pipeline = Gst.parse_launch(
    "playbin uri=https://gstreamer.freedesktop.org/data/media/sintel_trailer-480p.webm"
)

pipeline.set_state(Gst.State.PLAYING)

bus = pipeline.get_bus()
msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS)
pipeline.set_state(Gst.State.NULL)
