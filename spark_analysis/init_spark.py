from pyspark.sql import SparkSession

def create_spark_session(app_name="TransitAnalysis"):
    """
    创建并配置 SparkSession
    """
    spark = SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.warehouse.dir", "warehouse") \
        .enableHiveSupport() \
        .getOrCreate()
    return spark

if __name__ == "__main__":
    spark = create_spark_session()
    print("Spark Session created successfully.")
    # TODO: 添加数据读取与处理逻辑
