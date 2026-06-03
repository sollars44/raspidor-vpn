 package org.raspidor.bypass;

import android.content.Intent;
import android.net.VpnService;
import android.os.ParcelFileDescriptor;
import java.io.File;
import java.io.IOException;

public class BypassVpnService extends VpnService implements Runnable {
    private Thread mThread = null;
    private ParcelFileDescriptor mInterface = null;
    private Process mProcess = null;
    private String mSplitSize = "2";
    private String mHostListPath = "";

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            String action = intent.getStringExtra("action");
            if ("STOP".equals(action)) {
                stopVpn();
                return START_NOT_STICKY;
            }
            mSplitSize = intent.getStringExtra("split");
            if (mSplitSize == null) mSplitSize = "2";
            mHostListPath = intent.getStringExtra("hostlist");
        }

        if (mThread != null) {
            mThread.interrupt();
        }
        mThread = new Thread(this, "BypassVpnThread");
        mThread.start();
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        stopVpn();
        super.onDestroy();
    }

    @Override
    public void run() {
        try {
            // 1. Запуск бинарника ByeDPI (ciadpi) внутри изолированной памяти приложения
            startByeDpiCore();

            // 2. Настройка и поднятие системного VPN-туннеля
            Builder builder = new Builder();
            builder.setMtu(1500)
                   .addAddress("10.0.0.2", 32)
                   .addRoute("0.0.0.0", 0) // Заворачиваем абсолютно весь трафик телефона
                   .addDnsServer("8.8.8.8")
                   .addDnsServer("1.1.1.1")
                   .setSession("RASPIDOR Bypass");

            mInterface = builder.establish();

            // Удерживаем поток активным, пока VPN работает
            while (!Thread.interrupted()) {
                Thread.sleep(2000);
            }
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            stopVpn();
        }
    }

    private void startByeDpiCore() {
        try {
            File appFilesDir = getFilesDir();
            // Путь к бинарнику ciadpi, распакованному Kivy/Buildozer
            File binFile = new File(appFilesDir, "app/ciadpi");
            
            if (binFile.exists()) {
                binFile.setExecutable(true);
                
                // Базовые аргументы запуска локального SOCKS5 на порту 1080
                String cmd = binFile.getAbsolutePath() + " -i 127.0.0.1 -p 1080 --split " + mSplitSize;
                
                // Добавляем список сайтов, если он передан
                if (mHostListPath != null && !mHostListPath.isEmpty()) {
                    cmd += " --hostlist " + mHostListPath;
                }
                
                mProcess = Runtime.getRuntime().exec(cmd);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private void stopVpn() {
        if (mThread != null) {
            mThread.interrupt();
            mThread = null;
        }
        if (mProcess != null) {
            mProcess.destroy();
            mProcess = null;
        }
        if (mInterface != null) {
            try {
                mInterface.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
            mInterface = null;
        }
    }
}
