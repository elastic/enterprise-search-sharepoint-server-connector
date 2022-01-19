import os
import logging
import logging.config

# Uncomment this line to include dependency that allows to
# output logs in ECS-compatible format
# import ecs_logging

log_level = os.environ.get("LOGLEVEL", "WARN")
logger = logging.getLogger()
logger.propagate = False
logger.setLevel(log_level)

handler = logging.StreamHandler()
# Uncomment the following lines to output logs in ECS-compatible format
# formatter = ecs_logging.StdlibFormatter()
# handler.setFormatter(formatter)
handler.setLevel(log_level)
logger.addHandler(handler)
