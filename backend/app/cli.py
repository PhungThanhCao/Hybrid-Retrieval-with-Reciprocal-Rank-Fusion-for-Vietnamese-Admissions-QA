from .ingestion.indexer import build_index
if __name__ == '__main__':
    docs,chunks=build_index(); print(f'Đã lập chỉ mục {docs} tài liệu, {chunks} đoạn.')
