import datetime


class SimpleLogger:
    """Ultra-simple logger with static methods."""
    
    _logfile_path = None
    _logtime = None

    @staticmethod
    def setup(logfile_path = None, logtime = None):
        SimpleLogger._logfile_path = logfile_path if logfile_path else None
        SimpleLogger._logtime = logtime if logtime else datetime.now()

    LEVEL_EMOJIS = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨'
    }

    @staticmethod
    def log(self, msg, level='info'):
        logtext = f"[{datetime.now().strftime('%H:%M:%S')}] {SimpleLogger.LEVEL_EMOJIS[level.upper()]} {msg}"

        if SimpleLogger.logfile_path:
            with open(SimpleLogger.logfile_path, 'a') as f:
                f.write(logtext + '\n')
        else:
            print(logtext)

    @staticmethod
    def debug(msg): 
        SimpleLogger.log(msg, 'DEBUG')

    @staticmethod
    def info(msg): 
        SimpleLogger.log(msg, 'INFO')

    @staticmethod
    def warning(msg): 
        SimpleLogger.log(msg, 'WARNING')

    @staticmethod
    def error(msg): 
        SimpleLogger.log(msg, 'ERROR')

    @staticmethod
    def critical(msg): 
        SimpleLogger.log(msg, 'CRITICAL')

# Usage:
#SimpleLogger.info("Message here")
#SimpleLogger.error("Error here")