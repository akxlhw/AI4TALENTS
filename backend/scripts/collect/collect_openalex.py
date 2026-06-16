"""
OpenAlex 完整数据采集脚本

运行方式:
    cd backend
    python scripts/collect_openalex.py
"""
import sys

sys.path.insert(0, '.')

import json
import sqlite3
import time

import requests

OPENALEX_BASE_URL = "https://api.openalex.org"
POLITE_POOL = "mailto:research@example.com"


def main():
    print('='*70)
    print('OpenAlex 完整数据采集')
    print('='*70)
    print()

    conn = sqlite3.connect('talent.db')
    cursor = conn.cursor()

    # 获取配置的 venues
    cursor.execute('SELECT collect_sources FROM core_tech_domain WHERE tech_domain_id = 1')
    row = cursor.fetchone()
    venues = json.loads(row[0]) if row and row[0] else []

    print(f'配置的采集源: {len(venues)} 个')
    print()

    stats = {'sources': 0, 'works': 0, 'authors': 0, 'institutions': 0}
    all_author_ids = set()
    all_institution_ids = set()

    # 1. 采集 Sources
    print('步骤 1/4: 采集 Sources (期刊/会议)')
    print('-'*50)

    for venue in venues:
        openalex_id = venue.get('openalex_id')
        if not openalex_id:
            continue

        try:
            url = f'{OPENALEX_BASE_URL}/sources/{openalex_id}'
            resp = requests.get(url, params={'mailto': POLITE_POOL}, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                source_id = data.get('id', '').split('/')[-1]

                cursor.execute('''
                    INSERT OR REPLACE INTO openalex_source
                    (source_id, display_name, type, works_count, cited_by_count, h_index, is_oa, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    source_id,
                    data.get('display_name'),
                    data.get('type'),
                    data.get('works_count', 0),
                    data.get('cited_by_count', 0),
                    data.get('summary_stats', {}).get('h_index', 0),
                    1 if data.get('is_oa') else 0,
                    json.dumps(data)
                ))

                stats['sources'] += 1
                print(f'  {data.get("display_name")}: {data.get("works_count", 0):,} works')

            time.sleep(0.3)

        except Exception as e:
            print(f'  错误: {e}')

    conn.commit()

    # 2. 采集 Works
    print()
    print('步骤 2/4: 采集 Works (作品/论文)')
    print('-'*50)

    for venue in venues:
        openalex_id = venue.get('openalex_id')
        venue_name = venue.get('name', 'Unknown')
        if not openalex_id:
            continue

        print(f'\n  采集 {venue_name}...')

        page = 1
        per_page = 200
        max_pages = 50
        venue_works = 0

        while page <= max_pages:
            params = {
                'filter': f'primary_location.source.id:{openalex_id}',
                'per-page': per_page,
                'page': page,
                'mailto': POLITE_POOL,
                'sort': 'cited_by_count:desc',
            }

            try:
                resp = requests.get(f'{OPENALEX_BASE_URL}/works', params=params, timeout=60)

                if resp.status_code != 200:
                    break

                data = resp.json()
                works = data.get('results', [])
                if not works:
                    break

                for work in works:
                    work_id = work.get('id', '').split('/')[-1]

                    author_ids = []
                    for a in work.get('authorships', []):
                        aid = a.get('author', {}).get('id', '')
                        if aid:
                            author_ids.append(aid.split('/')[-1])
                            all_author_ids.add(aid)

                    for a in work.get('authorships', []):
                        for inst in a.get('institutions', []):
                            iid = inst.get('id', '')
                            if iid:
                                all_institution_ids.add(iid)

                    cursor.execute('''
                        INSERT OR REPLACE INTO openalex_work
                        (work_id, title, doi, publication_year, type, cited_by_count,
                         source_id, source_name, author_count, author_ids, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        work_id,
                        work.get('title'),
                        work.get('doi'),
                        work.get('publication_year'),
                        work.get('type'),
                        work.get('cited_by_count', 0),
                        openalex_id,
                        venue_name,
                        len(author_ids),
                        json.dumps(author_ids),
                        json.dumps(work)
                    ))

                    venue_works += 1
                    stats['works'] += 1

                meta = data.get('meta', {})
                total = meta.get('count', 0)
                if page * per_page >= total:
                    break

                if page % 10 == 0:
                    conn.commit()
                    print(f'    已采集 {venue_works:,} 作品')

                page += 1
                time.sleep(0.5)

            except Exception as e:
                print(f'    错误: {e}')
                break

        conn.commit()
        print(f'    完成: {venue_works:,} 作品')

    print(f'\n  累计作品: {stats["works"]:,}')
    print(f'  发现作者: {len(all_author_ids):,}')
    print(f'  发现机构: {len(all_institution_ids):,}')

    # 3. 采集 Authors
    print()
    print('步骤 3/4: 采集 Authors (作者)')
    print('-'*50)

    cursor.execute('SELECT source_record_id FROM core_talent')
    existing = set(row[0].split('/')[-1] for row in cursor.fetchall() if row[0])
    new_authors = list(all_author_ids - existing)[:5000]

    print(f'  采集 {len(new_authors):,} 位作者')

    for i, author_id in enumerate(new_authors):
        try:
            url = f'{OPENALEX_BASE_URL}/authors/{author_id}'
            resp = requests.get(url, params={'mailto': POLITE_POOL}, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                insts = data.get('last_known_institutions', [])

                cursor.execute('''
                    INSERT OR REPLACE INTO openalex_author
                    (author_id, display_name, orcid, works_count, cited_by_count,
                     h_index, last_known_institution, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    author_id,
                    data.get('display_name'),
                    data.get('orcid'),
                    data.get('works_count', 0),
                    data.get('cited_by_count', 0),
                    data.get('summary_stats', {}).get('h_index', 0),
                    insts[0].get('display_name') if insts else None,
                    json.dumps(data)
                ))

                stats['authors'] += 1

            if (i + 1) % 100 == 0:
                conn.commit()
                print(f'    进度: {i+1}/{len(new_authors)}')

            time.sleep(0.3)

        except Exception:
            pass

    conn.commit()

    # 4. 采集 Institutions
    print()
    print('步骤 4/4: 采集 Institutions (机构)')
    print('-'*50)

    inst_list = list(all_institution_ids)[:1000]
    print(f'  采集 {len(inst_list)} 个机构')

    for i, inst_id in enumerate(inst_list):
        try:
            short_id = inst_id.split('/')[-1]
            url = f'{OPENALEX_BASE_URL}/institutions/{short_id}'
            resp = requests.get(url, params={'mailto': POLITE_POOL}, timeout=30)

            if resp.status_code == 200:
                data = resp.json()

                cursor.execute('''
                    INSERT OR REPLACE INTO openalex_institution
                    (institution_id, display_name, country_code, type,
                     works_count, cited_by_count, homepage_url, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    short_id,
                    data.get('display_name'),
                    data.get('country_code'),
                    data.get('type'),
                    data.get('works_count', 0),
                    data.get('cited_by_count', 0),
                    data.get('homepage_url'),
                    json.dumps(data)
                ))

                stats['institutions'] += 1

            time.sleep(0.3)

        except Exception:
            pass

    conn.commit()

    # 最终统计
    print()
    print('='*70)
    print('采集完成!')
    print('='*70)
    print(f'  Sources (期刊/会议): {stats["sources"]}')
    print(f'  Works (作品): {stats["works"]:,}')
    print(f'  Authors (作者): {stats["authors"]:,}')
    print(f'  Institutions (机构): {stats["institutions"]}')

    conn.close()


if __name__ == '__main__':
    main()
