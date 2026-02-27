import { mqtt, iot } from 'aws-iot-device-sdk-v2'
import * as dotenv from 'dotenv'

dotenv.config();

async function execute() {
  console.log("start execute");

  const region = process.env.AWS_REGION || "ap-northeast-1"
  const endpoint = process.env.AWS_IOT_ENDPOINT
  const accessKeyId = process.env.AWS_ACCESS_KEY_ID
  const secretAccessKey = process.env.AWS_SECRET_ACCESS_KEY

  if (!endpoint || !accessKeyId || !secretAccessKey) {
    console.error("One or more AWS configure env variables not set")
    return;
  }

  const config_buider = iot.AwsIotMqttConnectionConfigBuilder.new_builder_for_websocket()
        .with_clean_session(true)
        .with_client_id(`vscode-prototype-${Date.now()}`)
        .with_endpoint(endpoint)
        .with_credentials(region, accessKeyId, secretAccessKey);

  const config = config_buider.build()
  const client = new mqtt.MqttClient()
  const connection = client.new_connection(config)

  try {
    await connection.connect()
    console.log("Successfly connect to AWS IoT Core!")

    const topic = "hackathon/run/test"

    await connection.subscribe(topic, mqtt.QoS.AtLeastOnce, (topic, payload) => {
      const message = new TextDecoder("utf-8").decode(new Uint8Array(payload as ArrayBuffer));
      console.log(`Received signals: topic: ${topic}`);
      console.log(`contents: ${message}`);

      try {
        const data = JSON.parse(message);
        if (data.is_running) {
          console.log("ex: hackathon-running start");
        } else {
          console.log("ex: hackathon-running stop");
        }
      } catch (e) {
        console.error("Json parse failed", e);
      }
    });

    console.log(`Watching topic ${topic}, waiting for signal from Apple Watch...`);
  } catch (error) {
    console.error("Connection error", error);
  }
}

execute();
