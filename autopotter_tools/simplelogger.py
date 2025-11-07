import datetime
import inspect

class Logger:
    """Ultra-simple logger with static methods."""
    
    _logfile_path = None
    _logtime = None
    _loglevel = 2

    @staticmethod
    def setup(logfile_path = None, logtime = None, loglevel = None):
        Logger._logfile_path = logfile_path if logfile_path else Logger._logfile_path
        Logger._logtime = logtime if logtime else (Logger._logtime if Logger._logtime else datetime.datetime.now())
        if loglevel is not None:
            # Convert string level name to number if needed
            if isinstance(loglevel, str):
                Logger._loglevel = Logger.LEVELS.get(loglevel.upper(), Logger._loglevel)
            else:
                Logger._loglevel = loglevel


    LEVELS = {
        'DEBUG': 1, 
        'INFO': 2, 
        'WARNING': 3,
        'ERROR': 4
    }

    LEVEL_EMOJIS = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌'
    }

    @staticmethod
    def log(msg, level='info'):
        if Logger.LEVELS[level.upper()] < Logger._loglevel:
            return
        
        frame = inspect.currentframe().f_back.f_back
        caller_name = frame.f_code.co_name if frame else "unknown"

        logtext = f"[ {caller_name} ] {Logger.LEVEL_EMOJIS[level.upper()]}   {msg}"

        if Logger._logfile_path:
            with open(Logger._logfile_path, 'a') as f:
                f.write(logtext + '\n')
        else:
            print(logtext)

    @staticmethod
    def debug(msg): 
        Logger.log(msg, 'DEBUG')

    @staticmethod
    def info(msg): 
        Logger.log(msg, 'INFO')

    @staticmethod
    def warning(msg): 
        Logger.log(msg, 'WARNING')

    @staticmethod
    def error(msg): 
        Logger.log(msg, 'ERROR')

# Usage:
#SimpleLogger.info("Message here")
#SimpleLogger.error("Error here")