import sys
import gi
import logging

gi.require_versions({"GLib": "2.0", "GObject": "2.0", "Gst": "1.0"})

from gi.repository import Gst, GLib, GObject  # noqa: F401


logging.basicConfig(level=logging.DEBUG, format="[%(name)s] [%(levelname)8s] - %(message)s")
logger = logging.getLogger(__name__)


class TimeManagementPipeline:
    def __init__(self):
        self.playing = False
        self.terminate = False
        self.seek_enabled = False
        self.seek_done = False
        self.duration = Gst.CLOCK_TIME_NONE

        self.pipeline = Gst.Pipeline.new("test-pipeline")
        self.playbin = Gst.ElementFactory.make("playbin", "playbin")

        if not self.pipeline or not self.playbin:
            logging.error("Not all elements could be created.")
            sys.exit(1)

            self.pipeline.add(self.playbin)

        self.playbin.set_property("uri",
                                  "https://gstreamer.freedesktop.org/data/media/sintel_trailer-480p.webm")


def handle_message(msg: Gst.Message, data: TimeManagementPipeline):
    if msg.type == Gst.MessageType.ERROR:
        err, debug_info = msg.parse_error()
        logger.error(f"Error received from element {msg.src.get_name()}: {err.message}")
        logger.error(f"Debug information: {debug_info if debug_info else None}")
        data.terminate = True
    elif msg.type == Gst.MessageType.EOS:
        logger.info("End-Of-Stream reached")
        data.terminate = True
    elif msg.type == Gst.MessageType.DURATION_CHANGED:
        data.duration = Gst.CLOCK_TIME_NONE
    elif msg.type == Gst.MessageType.STATE_CHANGED:
        if msg.src == data.playbin:
            old_state, new_state, pending_state = msg.parse_state_changed()
            old_state_name = Gst.Element.state_get_name(old_state)
            new_state_name = Gst.Element.state_get_name(new_state)
            logging.info(f"Pipeline state changed from {old_state_name} to {new_state_name}.")
            data.playing = (new_state == Gst.State.PLAYING)
            if data.playing:
                query = Gst.Query.new_seeking(Gst.Format.TIME)
                ok = data.playbin.query(query)
                if ok:
                    format, data.seek_enabled, start, end = query.parse_seeking()
                    if data.seek_enabled:
                        logging.info(f"Seeking is ENABLED from {start} to {end}.")
                    else:
                        logging.info("Seeking is disabled for this stream.")

                else:
                    logging.error("Seeking query failed")
    else:
        logging.error("Unexpected message received")


def main():
    Gst.init(sys.argv[1:])

    data = TimeManagementPipeline()

    state = data.playbin.set_state(Gst.State.PLAYING)
    if state == Gst.StateChangeReturn.FAILURE:
        logging.error("Unable to set the pipeline to the playing state.")
        sys.exit(1)

    bus = data.playbin.get_bus()

    while not data.terminate:
        msg = bus.timed_pop_filtered(100 * Gst.MSECOND,
                                     Gst.MessageType.STATE_CHANGED |
                                     Gst.MessageType.ERROR |
                                     Gst.MessageType.EOS |
                                     Gst.MessageType.DURATION_CHANGED)

        if msg is not None:
            handle_message(msg, data)
        else:
            # We got no message, this means the timeout has expired
            if data.playing:
                ok, current = data.playbin.query_position(Gst.Format.TIME)
                if not ok:
                    logging.error("Could not query current position.")

                # If we didn't know it yet, query the duration of the stream
                if data.duration == Gst.CLOCK_TIME_NONE:
                    ok, data.duration = data.playbin.query_duration(Gst.Format.TIME)
                    if not ok:
                        logging.error("Could not query current duration.")

                # Print current position and total duration
                logging.info(f"Position {current / 1000000000} / {data.duration / 1000000000}")

                # If seeking is enabled, we have not done it yet, and the time is right, seek
                if data.seek_enabled and not data.seek_done and current > 10 * Gst.SECOND:
                    logging.info("Reached 10s, performing seek...")
                    data.playbin.seek_simple(Gst.Format.TIME,
                                             Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                             30 * Gst.SECOND)
                    data.seek_done = True

    data.playbin.set_state(Gst.State.NULL)


if __name__ == "__main__":
    main()
