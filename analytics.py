import pandas as pd


def read_table_from_link(url):
    try:
        if 'docs.google.com/spreadsheets' in url:
            base_url = url.split('/edit')[0]
            download_url = f'{base_url}/export?format=csv'
            return pd.read_csv(download_url)

        elif url.endswith('.csv'):
            return pd.read_csv(url)

        elif url.endswith('.xlsx') or url.endswith('.xls'):
            return pd.read_excel(url, engine='openpyxl')

        else:
            return None

    except Exception as e:
        return None











