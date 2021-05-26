import dotenv from "dotenv";
import playerSound from "play-sound";
import noble from "@abandonware/noble";
import { PythonShell } from "python-shell";
import mqtt from "mqtt";

dotenv.config();
const player = playerSound({});

const mqttClient  = mqtt.connect(process.env.MQTT);
let mqttConnected = false;

mqttClient.on('connect', () => {
  console.log('mqtt connected')
  mqttConnected = true;
})

mqttClient.on('error', (e) => {
  console.log(e)
})

const initHeartbeat = () => {
  setInterval(() => {
    if (!mqttConnected) return;
    mqttClient.publish('toTransform.heatbeat', null);
  }, 1000);
};

initHeartbeat();

const pyshell = new PythonShell('main.py', {pythonPath: process.env.PYTHON_PATH, mode: 'text' });

pyshell.on('message',  (message) => {
  if (!mqttConnected) return;
  mqttClient.publish('toTransform.data', message)
});

const themeSound = () => {
  player.play('sound/q_theme.wav', err => {
    if (err) throw err
  })
}

const loopTheme = () => {
  themeSound()
  setTimeout(() => {
    loopTheme()
  }, 116000)
}

const jumpSound = () => {
  player.play('sound/jump.wav', err => {
    if (err) throw err
  })
}

const moveSound = () => {
  player.play('sound/crawl.wav', err => {
    if (err) throw err
  })
}

const serviceUuids = ['FFFF'];
const allowDuplicates = false;

noble.on('stateChange', state => {
  if (state === 'poweredOn') {
    noble.startScanning(serviceUuids, allowDuplicates);
  } else {
    noble.stopScanning();
  }
});

noble.on('discover', peripheral => {
  connectAuAsync(peripheral).then(() => null);
  peripheral.on('disconnect', error => {
    console.log('disconnect');
    connectAuAsync(peripheral).then(() => null);
  });
});

const peripheralConnect = (peripheral) => new Promise((resolve, reject) => {
  peripheral.connect(error => {
    if (error) return reject(error);
    resolve();
  });
});

const discoverServices = (peripheral) => new Promise((resolve, reject) => {
  peripheral.discoverServices(serviceUuids.map( s => s.toLowerCase()), (error, services) => {
    if (error) return reject(error);
    resolve(services)
  })
});

const discoverCharacteristics = (service) => new Promise((resolve, reject) => {
  service.discoverCharacteristics(null, (error, characteristics) => {
    if (error) return reject(error);
    const jump = characteristics[0];
    console.log('discovered jump characteristic');
    const move = characteristics[1];
    console.log('discovered move characteristic');
    resolve({jump, move})
  })
});

const jumpAction = () => {
  jumpSound();
  pyshell.send('jump');
  setTimeout(() => {
    moveSound();
    pyshell.send('jump');
    pyshell.send('move');
  }, 100);
}

const moveAction = () => {
  moveSound();
  pyshell.send('move');
  setTimeout(() => {
    moveSound();
    pyshell.send('move');
  }, 200);
}

const connectAuAsync = async (peripheral) => {
  await peripheralConnect(peripheral);
  console.log(`connected to peripheral: ${peripheral.uuid}`);
  const services = await discoverServices(peripheral);
  const service = services[0];
  console.log('discovered service');
  const {jump, move} = await discoverCharacteristics(service);

  jump.on('data', (data, isNotification) => {
    console.log('w is now: ', `${data.readUInt16BE(0)}%`);
    jumpAction();
  });

  move.on('data', (data, isNotification) => {
    console.log('d is now: ', `${data.readUInt16BE(0)}%`);
    moveAction();
  });

  // to enable notify
  [jump, move].forEach( characteristic => {
    characteristic.subscribe(error => {
      if (error) throw error;
      console.log('notification on');
    });
  })
};

// process.on('SIGINT', async () => {
//   // end the input stream and allow the process to exit
//   await pyshell.end();
//   await pyshell.kill();
//   process.exit();
// });
