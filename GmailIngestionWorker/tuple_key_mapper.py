class TupleKeyMapper:
    """
    Maps a tuple to a string key for Kafka messages.
    """
    SEPRATOR:str = ":"

    @staticmethod
    def map_tuple_to_key(tup: tuple) -> str:
        """
        Maps a tuple to a string key by joining its elements with a hyphen.
        """
        return TupleKeyMapper.SEPRATOR.join(map(str, tup))

    @staticmethod
    def map_key_to_tuple(key: str) -> tuple:
        """
        Maps a string key back to a tuple by splitting it on hyphens.
        """
        return tuple(key.split(TupleKeyMapper.SEPRATOR))