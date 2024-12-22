import sys
import gi
import logging

gi.require_versions({"GLib": "2.0", "GObject": "2.0", "Gst": "1.0"})

from gi.repository import Gst, GLib, GObject

logging.basicConfig(level=logging.DEBUG, format="[%(name)s] [%(levelname)8s] - %(message)s")
logger = logging.getLogger(__name__)


def pad_added_handler(source, new_pad: Gst.Pad, convert):
    sink_pad: Gst.Pad = convert.get_static_pad("sink")

    logging.info(f"Received new pad '{new_pad.name}' from '{source.name}'")

    if sink_pad.is_linked():
        logging.info("Pad is already linked. Ignoring.")
        return

    new_pad_caps = new_pad.get_current_caps()
    new_pad_struct = new_pad_caps.get_structure(0)
    new_pad_type = new_pad_struct.get_name()
    if not new_pad_type.startswith("audio/x-raw"):
        logging.warning(f"New pad has type '{new_pad_type}' which is not raw audio. Ignoring.")
        return

    if new_pad.link(sink_pad) != Gst.PadLinkReturn.OK:
        logging.warning(f"New pad has type '{new_pad_type}' but link failed.")
    else:
        logging.info(f"Link succeeded (type '{new_pad_type}').")


def main():
    Gst.init(sys.argv[1:])
    pipeline = Gst.Pipeline.new("test-pipeline")
    source = Gst.ElementFactory.make("uridecodebin", "source")
    convert = Gst.ElementFactory.make("audioconvert", "convert")
    resample = Gst.ElementFactory.make("audioresample", "resample")
    sink = Gst.ElementFactory.make("autoaudiosink", "sink")

    if not pipeline or not source or not convert or not resample or not sink:
        logging.error("Not all elemens could be created.")
        sys.exit(1)

    pipeline.add(source)
    pipeline.add(convert)
    pipeline.add(resample)
    pipeline.add(sink)

    if not convert.link(resample) or not resample.link(sink):
        logging.error("Elements could not be linked.")
        sys.exit(1)

    source.set_property("uri", "https://gstreamer.freedesktop.org/data/media/sintel_trailer-480p.webm")
    source.connect("pad_added", pad_added_handler, convert)

    status = pipeline.set_state(Gst.State.PLAYING)
    if status == Gst.StateChangeReturn.FAILURE:
        logging.error("Unable to set the pipeline to the playing state.")
        sys.exit(1)

    bus = pipeline.get_bus()
    terminate = False
    while not terminate:
        msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE,
                                     Gst.MessageType.STATE_CHANGED |
                                     Gst.MessageType.ERROR |
                                     Gst.MessageType.EOS)

        if msg:
            if msg.type == Gst.MessageType.ERROR:
                err, debug_info = msg.parse_error()
                logger.error(f"Error received from element {msg.src.get_name()}: {err.message}")
                logger.error(f"Debug information: {debug_info if debug_info else None}")
                terminate = True
            elif msg.type == Gst.MessageType.EOS:
                logger.info("End-Of-Stream reached")
                terminate = True
            elif msg.type == Gst.MessageType.STATE_CHANGED:
                if msg.src == pipeline:
                    old_state, new_state, pending_state = msg.parse_state_changed()
                    old_state = Gst.Element.state_get_name(old_state)
                    new_state = Gst.Element.state_get_name(new_state)
                    logging.info(f"Pipeline state changed from {old_state} to {new_state}.")
            else:
                logger.error("Unexpected message received.")
                terminate = True

    pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    main()
