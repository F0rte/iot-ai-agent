// AgentController/ContentView.swift
import SwiftUI
import AWSCore
import AWSIoT

struct ContentView: View {
    @State private var isConnected = false
    @State private var iotDataManager: AWSIoTDataManager?

    var body: some View {
        VStack(spacing: 40) {
            Text(isConnected ? "✅ AWS IoT 接続済み" : "⏳ 接続中...")
                .foregroundColor(isConnected ? .green : .gray)
                .font(.title2)
                .bold()

            Button(action: {
                publishRunStatus()
            }) {
                Text("🏃‍♂️ 走る (テスト送信)")
                    .font(.title)
                    .bold()
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(isConnected ? Color.blue : Color.gray)
                    .foregroundColor(.white)
                    .cornerRadius(15)
            }
            .disabled(!isConnected) // 接続されるまでボタンを押せなくする
            .padding(.horizontal, 40)
        }
        .onAppear {
            setupAWSConnection()
        }
    }

    // 起動時にAWS IoT CoreへWebSocketで接続する処理
    func setupAWSConnection() {
        let credentialsProvider = AWSStaticCredentialsProvider(
            accessKey: Secrets.accessKey,
            secretKey: Secrets.secretKey
        )

        guard let endpointURL = URL(string: "https://\(Secrets.iotEndpoint)") else { return }
        let endpoint = AWSEndpoint(url: endpointURL)

        let iotConfig = AWSServiceConfiguration(
            region: .APNortheast1,
            endpoint: endpoint,
            credentialsProvider: credentialsProvider
        )

        AWSIoTDataManager.register(with: iotConfig!, forKey: "HackathonIoTManager")
        iotDataManager = AWSIoTDataManager(forKey: "HackathonIoTManager")

        let clientId = "swift-client-\(UUID().uuidString.prefix(8))"
        iotDataManager?.connectUsingWebSocket(withClientId: clientId, cleanSession: true) { status in
            DispatchQueue.main.async {
                if status == .connected {
                    self.isConnected = true
                    print("✅ AWS IoT Coreに接続成功！")
                } else {
                    print("🔄 ステータス変更: \(status.rawValue)")
                }
            }
        }
    }

    // ボタンを押した時にデータを送信する処理
    func publishRunStatus() {
        let topic = "hackathon/run/test"
        // 送信するダミーデータ
        let payloadString = "{\"is_running\": true, \"bpm\": 135}"

        iotDataManager?.publishString(
            payloadString,
            onTopic: topic,
            qoS: .messageDeliveryAttemptedAtMostOnce
        )
        print("📨 データを送信しました: \(payloadString)")
    }
}

#Preview {
    ContentView()
}
