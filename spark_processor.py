from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.sql.functions import from_json
from pyspark.sql.types import StructType, StringType, IntegerType
from pyspark.sql.functions import regexp_replace

spark = SparkSession.builder \
    .appName("HackerNewsProcessor") \
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


query = df_json.writeStream \
    .outputMode("append") \
    .format("console") \
    .start()

query.awaitTermination()