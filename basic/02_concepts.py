import sys
import gi
import logging

gi.require_versions({"GLib": "2.0", "GObject": "2.0", "Gst": "1.0"})

from gi.repository import Gst, GLib, GObject

logging.basicConfig(level=logging.DEBUG, format="[%(name)s] [%(levelname)8s] - %(message)s")
logger = logging.getLogger(__name__)

Gst.init(sys.argv[1:])

source = Gst.ElementFactory.make("videotestsrc", "source")
vertigotv = Gst.ElementFactory.make("vertigotv", "vertigo")
videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
videoscale = Gst.ElementFactory.make("videoscale", "videoscale")
capsfilter = Gst.ElementFactory.make("capsfilter", "resolution")
capsfilter.set_property("caps", Gst.Caps.from_string("video/x-raw,width=(int)1920,height=(int)1080"))
sink = Gst.ElementFactory.make("autovideosink", "sink")

pipeline = Gst.Pipeline.new("test-pipeline")

if not source or not sink or not pipeline:
    logger.error("Not all elements could be created.")
    sys.exit(1)

pipeline.add(source)
pipeline.add(vertigotv)
pipeline.add(videoconvert)
pipeline.add(videoscale)
pipeline.add(capsfilter)
pipeline.add(sink)
if not source.link(vertigotv) \
   or not vertigotv.link(videoconvert) \
   or not videoconvert.link(videoscale) \
   or not videoscale.link(capsfilter) \
   or not capsfilter.link(sink):
    logger.error("Elements could not be linked.")
    sys.exit(1)

source.set_property("pattern", 0)
ret = pipeline.set_state(Gst.State.PLAYING)
if ret == Gst.StateChangeReturn.FAILURE:
    logger.error("Unable to set the pipeline to the playing state.")
    sys.exit(1)

bus = pipeline.get_bus()
msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE,
                             Gst.MessageType.ERROR |
                             Gst.MessageType.EOS)

if msg:
    if msg.type == Gst.MessageType.ERROR:
        err, debug_info = msg.parse_error()
        logger.error(f"Error received from element {msg.src.get_name()}: {err.message}")
        logger.error(f"Debug information: {debug_info if debug_info else None}")
    elif msg.type == Gst.MessageType.EOS:
        logger.info("End-Of-Stream reached")
    else:
        logger.error("Unexpected message received.")

pipeline.set_state(Gst.State.NULL)
