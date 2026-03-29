"""
测试采集服务脚本
用于验证采集执行器是否能正常工作
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import requests
from datetime import datetime

OPENALEX_BASE_URL = "https://api.openalex.org"
POLITE_POOL_EMAIL = "mailto:test@example.com"


def test_openalex_api():
    """测试 OpenAlex API 是否可用"""
    print("=" * 60)
    print("测试 1: OpenAlex API 连通性")
    print("=" * 60)

    try:
        # 测试 Works API
        response = requests.get(
            f"{OPENALEX_BASE_URL}/works",
            params={"per_page": 1, "mailto": POLITE_POOL_EMAIL},
            timeout=30
        )
        print(f"  Works API 状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            count = data.get('meta', {}).get('count', 0)
            print(f"  Works 总数: {count:,}")
        else:
            print(f"  错误: {response.text[:200]}")
            return False

        # 测试 Authors API
        response = requests.get(
            f"{OPENALEX_BASE_URL}/authors/A5063258585",  # 随机选择一个作者ID
            params={"mailto": POLITE_POOL_EMAIL},
            timeout=30
        )
        print(f"  Authors API 状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"  示例作者: {data.get('display_name')}")
            print(f"  Works count: {data.get('works_count')}")
            print(f"  h-index: {data.get('summary_stats', {}).get('h_index')}")
        else:
            print(f"  错误: {response.text[:200]}")

        return True

    except Exception as e:
        print(f"  异常: {e}")
        return False


def test_venue_search():
    """测试 venue 搜索"""
    print("\n" + "=" * 60)
    print("测试 2: Venue 搜索")
    print("=" * 60)

    test_venues = ["NeurIPS", "ICML", "CVPR"]

    for venue_name in test_venues:
        try:
            response = requests.get(
                f"{OPENALEX_BASE_URL}/sources",
                params={"search": venue_name, "per_page": 3, "mailto": POLITE_POOL_EMAIL},
                timeout=30
            )

            if response.status_code == 200:
                results = response.json().get('results', [])
                if results:
                    source = results[0]
                    print(f"  {venue_name}:")
                    print(f"    ID: {source.get('id')}")
                    print(f"    Name: {source.get('display_name')}")
                    print(f"    Type: {source.get('type')}")
                    print(f"    Works: {source.get('works_count', 0):,}")
                else:
                    print(f"  {venue_name}: 未找到")
            else:
                print(f"  {venue_name}: API 错误 {response.status_code}")

            time.sleep(0.5)

        except Exception as e:
            print(f"  {venue_name}: 异常 - {e}")

    return True


def test_works_from_venue():
    """测试从 venue 获取作品"""
    print("\n" + "=" * 60)
    print("测试 3: 从 Venue 获取作品")
    print("=" * 60)

    # NeurIPS 的 OpenAlex ID
    neurips_id = "S137534324"

    try:
        response = requests.get(
            f"{OPENALEX_BASE_URL}/works",
            params={
                "filter": f"primary_location.source.id:{neurips_id}",
                "per_page": 5,
                "mailto": POLITE_POOL_EMAIL
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            total = data.get('meta', {}).get('count', 0)
            works = data.get('results', [])

            print(f"  NeurIPS 作品总数: {total:,}")
            print(f"  获取到 {len(works)} 个作品示例:")

            for work in works[:3]:
                title = work.get('title', 'N/A')[:50]
                year = work.get('publication_year', 'N/A')
                authorships = work.get('authorships', [])
                authors = [a.get('author', {}).get('display_name', '') for a in authorships[:3]]
                print(f"    - {year}: {title}...")
                print(f"      作者: {', '.join(authors)}")

            return True
        else:
            print(f"  API 错误: {response.status_code}")
            return False

    except Exception as e:
        print(f"  异常: {e}")
        return False


def test_database_connection():
    """测试数据库连接"""
    print("\n" + "=" * 60)
    print("测试 4: 数据库连接")
    print("=" * 60)

    try:
        from sqlalchemy import create_engine, text
        from app.core.config import settings

        engine = create_engine(settings.DATABASE_SYNC_URL, echo=False)

        with engine.connect() as conn:
            # 检查表
            result = conn.execute(text("SELECT COUNT(*) FROM core_talent"))
            talent_count = result.scalar()
            print(f"  当前学者数: {talent_count}")

            result = conn.execute(text("SELECT COUNT(*) FROM core_school"))
            school_count = result.scalar()
            print(f"  当前学校数: {school_count}")

            result = conn.execute(text("SELECT COUNT(*) FROM core_country"))
            country_count = result.scalar()
            print(f"  国家数: {country_count}")

            # 检查技术要素
            result = conn.execute(text("SELECT tech_element_id, element_name FROM core_tech_element"))
            elements = result.fetchall()
            print(f"  技术要素:")
            for elem in elements:
                print(f"    - {elem[0]}: {elem[1]}")

        return True

    except Exception as e:
        print(f"  异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_school_creation():
    """测试学校创建逻辑"""
    print("\n" + "=" * 60)
    print("测试 5: 学校创建逻辑")
    print("=" * 60)

    try:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import sessionmaker
        from app.core.config import settings
        from app.models.school import School
        from app.models.country import Country

        engine = create_engine(settings.DATABASE_SYNC_URL, echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()

        # 检查是否有可用的国家
        result = session.execute(select(Country).limit(1))
        country = result.scalar_one_or_none()

        if country:
            print(f"  默认国家: {country.country_name_cn} (ID: {country.country_id})")

            # 测试创建学校
            test_school_name = f"测试学校_{datetime.now().strftime('%H%M%S')}"

            # 检查是否已存在
            existing = session.execute(
                select(School).where(School.school_name == test_school_name)
            ).scalar_one_or_none()

            if not existing:
                school = School(
                    school_name=test_school_name,
                    country_id=country.country_id,
                    is_visible=True,
                    status='active'
                )
                session.add(school)
                session.commit()
                print(f"  成功创建测试学校: {test_school_name} (ID: {school.school_id})")

                # 清理
                session.delete(school)
                session.commit()
                print(f"  已清理测试学校")
            else:
                print(f"  测试学校已存在")
        else:
            print(f"  错误: 没有可用的国家数据")
            return False

        session.close()
        return True

    except Exception as e:
        print(f"  异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("采集服务自测脚本")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = []

    results.append(("OpenAlex API", test_openalex_api()))
    results.append(("Venue 搜索", test_venue_search()))
    results.append(("作品获取", test_works_from_venue()))
    results.append(("数据库连接", test_database_connection()))
    results.append(("学校创建", test_school_creation()))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("所有测试通过！采集服务可以正常工作。")
    else:
        print("部分测试失败，请检查上述错误。")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
