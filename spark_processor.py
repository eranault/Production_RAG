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
                     .option("subscribe","dbz.hackernews.stories") \
                     .load()



df = df.selectExpr("CAST(value AS STRING) as raw")


outer_schema = StructType() \
    .add("payload", StructType()
         .add("after", StringType())  
         .add("op", StringType()))    # "c"=create, "u"=update, "d"=delete btw


df = df.select(from_json(col("raw"), outer_schema).alias("envelope"))


df = df.filter(col("envelope.payload.op") != "d")

#On va extraire le champ after (toujours au format json) et le parser pour avoir un dataframe avec les champs de l'histoire hackernews


df = df.select(col("envelope.payload.after").alias("after_str"))

story_schema = StructType() \
    .add("id", IntegerType()) \
    .add("title", StringType()) \
    .add("text", StringType()) \
    .add("url", StringType()) \
    .add("score", IntegerType())

df = df.select(from_json(col("after_str"), story_schema).alias("story")).select("story.*")

# Step 6: Clean HTML tags from the text field (same as before)
df = df.withColumn("text", regexp_replace("text", "<[^>]+>", ""))


df = df.select(to_json(struct("*")).alias("value"))

query = df.writeStream \
    .outputMode("append") \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("topic", "hackernews-processed") \
    .option("checkpointLocation", "C:/tmp/spark-checkpoint-dbz") \
    .start()

query.awaitTermination()



#on a aussi changé le checkpoint pour que spark reprenne from scratch et pas from le checkpoint de l'ancien code qui lisait d'une source différente, à adapter selon votre setup