from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.sql.functions import from_json
from pyspark.sql.types import StructType, StringType, IntegerType
from pyspark.sql.functions import regexp_replace
from pyspark.sql.functions import to_json, struct
import os

os.environ["HADOOP_HOME"] = "C:\\hadoop"
os.environ["JAVA_HOME"] = "C:\\Program Files\\Java\\jdk-17.0.18"
os.environ["PATH"] = "C:\\hadoop\\bin;" + os.environ.get("PATH", "") 

spark = SparkSession.builder \
    .appName("HackerNewsProcessor") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0") \
    .getOrCreate()
df = spark.readStream.format("kafka")\
                     .option("kafka.bootstrap.servers","localhost:9092")\
                     .option("subscribe","hackernews-stories") \
                     .load()



df= df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")


schema = StructType() \
    .add("id", IntegerType()) \
    .add("title", StringType()) \
    .add("text", StringType()) \
    .add("url", StringType()) \
    .add("score", IntegerType())



json_df = df.select(from_json(col("value"), schema).alias("story")).select("story.*")


df_json = json_df.withColumn("text", regexp_replace("text", "<[^>]+>", ""))


df_json = df_json.select(to_json(struct("*")).alias("value"))

query = df_json.writeStream \
    .outputMode("append") \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("topic", "hackernews-processed") \
    .option("checkpointLocation", "C:/tmp/spark-checkpoint") \
    .start()

query.awaitTermination()