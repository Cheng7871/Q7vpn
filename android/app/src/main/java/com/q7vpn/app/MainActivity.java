package com.q7vpn.app;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final int PICK_TXT = 77;
    private final ArrayList<Node> nodes = new ArrayList<>();
    private final ExecutorService executor = Executors.newFixedThreadPool(4);
    private LinearLayout list;
    private TextView summary;
    private TextView status;
    private Node selected;

    static class Node {
        String uri, name, protocol, host, country = "未知地区";
        int port;
        String latency = "未检测";
        Node(String u, String n, String p, String h, int po) {
            uri=u; name=n; protocol=p; host=h; port=po;
        }
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        buildUi();
    }

    private int dp(float v) { return (int)(v * getResources().getDisplayMetrics().density + 0.5f); }
    private TextView text(String value, int size, int color) {
        TextView t = new TextView(this);
        t.setText(value); t.setTextSize(size); t.setTextColor(color);
        return t;
    }
    private GradientButtonStyle unused; // marker for documentation; no custom view dependency

    private void buildUi() {
        int bg = Color.rgb(9,11,18), fg = Color.rgb(247,247,251), muted = Color.rgb(148,153,173);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL); root.setPadding(dp(20), dp(24), dp(20), dp(18));
        root.setBackgroundColor(bg);

        TextView title = text("Q7vpn", 34, fg); title.setGravity(Gravity.CENTER_VERTICAL);
        title.setTypeface(null, 1); root.addView(title);
        TextView subtitle = text("节点 · 诊断 · 安全连接", 14, muted);
        root.addView(subtitle, new LinearLayout.LayoutParams(-1, dp(32)));

        LinearLayout actions = new LinearLayout(this); actions.setOrientation(LinearLayout.HORIZONTAL);
        Button importBtn = new Button(this); importBtn.setText("导入 TXT");
        importBtn.setOnClickListener(v -> pickTxt());
        Button testBtn = new Button(this); testBtn.setText("检测延迟");
        testBtn.setOnClickListener(v -> testAll());
        actions.addView(importBtn, new LinearLayout.LayoutParams(0, dp(52), 1));
        actions.addView(testBtn, new LinearLayout.LayoutParams(0, dp(52), 1));
        root.addView(actions);

        summary = text("0 个节点 · 尚未检测", 15, muted);
        summary.setPadding(0, dp(12), 0, dp(8)); root.addView(summary);
        status = text("选择节点后，点击“交给客户端”可在兼容的代理客户端中继续连接。", 13, muted);
        status.setPadding(dp(14), dp(12), dp(14), dp(12));
        status.setBackgroundColor(Color.rgb(25,28,40)); root.addView(status);

        ScrollView scroll = new ScrollView(this);
        list = new LinearLayout(this); list.setOrientation(LinearLayout.VERTICAL);
        scroll.addView(list);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));

        TextView foot = text("说明：当前版本管理节点并交接给兼容客户端；尚未内置 VPN 代理核心。", 12, muted);
        foot.setPadding(0, dp(12), 0, 0); root.addView(foot);
        setContentView(root);
        redraw();
    }

    private void pickTxt() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("text/plain");
        startActivityForResult(i, PICK_TXT);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != PICK_TXT || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        Uri file = data.getData();
        int added = 0, duplicates = 0, invalid = 0;
        try (BufferedReader br = new BufferedReader(new InputStreamReader(getContentResolver().openInputStream(file), StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null && nodes.size() < 3000) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) continue;
                Node n = parse(line);
                if (n == null) { invalid++; continue; }
                boolean dup = false;
                for (Node old : nodes) if (old.uri.equals(n.uri)) { dup = true; break; }
                if (dup) duplicates++; else { nodes.add(n); added++; }
            }
            summary.setText(nodes.size() + " 个节点 · 新增 " + added + " · 重复 " + duplicates + " · 无效 " + invalid);
            status.setText("已导入配置。导入成功不代表节点可用；请运行延迟检测。");
            redraw();
        } catch (Exception e) {
            Toast.makeText(this, "读取文件失败：" + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private Node parse(String raw) {
        try {
            if (raw.startsWith("vless://")) {
                URI u = URI.create(raw);
                if (u.getHost() == null) return null;
                String name = u.getFragment() == null ? u.getHost() : URLDecoder.decode(u.getFragment(), "UTF-8");
                int p = u.getPort() > 0 ? u.getPort() : 443;
                return new Node(raw, name, "VLESS", u.getHost(), p);
            }
            if (raw.startsWith("ss://")) {
                String body = raw.substring(5).split("#",2)[0];
                String name = raw.contains("#") ? URLDecoder.decode(raw.substring(raw.indexOf('#')+1), "UTF-8") : "Shadowsocks 节点";
                // SS URI formats vary; only parse authority-style host:port safely in this MVP.
                int at = body.lastIndexOf('@');
                if (at < 0) return new Node(raw, name, "SS", "", 0);
                String auth = body.substring(at+1);
                int colon = auth.lastIndexOf(':');
                if (colon < 1) return null;
                String host = auth.substring(0, colon);
                int port = Integer.parseInt(auth.substring(colon+1).replaceAll("[/?].*$",""));
                return new Node(raw, name, "SS", host, port);
            }
        } catch (Exception ignored) {}
        return null;
    }

    private void testAll() {
        if (nodes.isEmpty()) { Toast.makeText(this, "请先导入 TXT", Toast.LENGTH_SHORT).show(); return; }
        status.setText("正在检测 TCP 端口可达性…这不是完整代理握手测试。");
        for (Node n : nodes) {
            if (n.host == null || n.host.isEmpty() || n.port < 1 || n.port > 65535) {
                n.latency = "无法检测"; continue;
            }
            executor.execute(() -> {
                long start = System.nanoTime();
                String result;
                try (Socket s = new Socket()) {
                    s.connect(new InetSocketAddress(n.host, n.port), 2500);
                    result = ((System.nanoTime()-start)/1_000_000L) + " ms";
                } catch (Exception e) { result = "不可达"; }
                final String value = result;
                runOnUiThread(() -> { n.latency = value; redraw(); });
            });
        }
    }

    private void redraw() {
        if (list == null) return;
        list.removeAllViews();
        for (Node n : nodes) {
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.VERTICAL); card.setPadding(dp(16),dp(14),dp(16),dp(14));
            LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(-1, -2); cp.setMargins(0,dp(8),0,dp(4));
            card.setBackgroundColor(Color.rgb(23,26,37)); list.addView(card, cp);

            TextView name = text(n.name, 17, Color.WHITE); name.setTypeface(null,1); card.addView(name);
            TextView meta = text(n.protocol + "  ·  " + n.host + (n.port > 0 ? ":"+n.port : "") + "  ·  " + n.country + "  ·  " + n.latency, 12, Color.rgb(159,164,185));
            meta.setPadding(0,dp(6),0,dp(8)); card.addView(meta);
            LinearLayout row = new LinearLayout(this);
            Button select = new Button(this); select.setText(selected == n ? "已选择" : "选择");
            select.setOnClickListener(v -> { selected=n; status.setText("已选择："+n.name+"。点击“交给客户端”继续连接。"); redraw(); });
            Button share = new Button(this); share.setText("交给客户端");
            share.setOnClickListener(v -> handoff(n));
            row.addView(select, new LinearLayout.LayoutParams(0,dp(48),1));
            row.addView(share, new LinearLayout.LayoutParams(0,dp(48),1));
            card.addView(row);
        }
    }

    private void handoff(Node n) {
        selected = n;
        Intent share = new Intent(Intent.ACTION_SEND);
        share.setType("text/plain");
        share.putExtra(Intent.EXTRA_SUBJECT, "Q7vpn 节点配置");
        share.putExtra(Intent.EXTRA_TEXT, n.uri);
        try {
            startActivity(Intent.createChooser(share, "选择兼容的代理客户端导入节点"));
            status.setText("已打开分享菜单。请在兼容客户端中导入配置，并在该客户端确认 VPN 系统授权。");
        } catch (Exception e) {
            Toast.makeText(this, "未找到可用的分享目标。", Toast.LENGTH_LONG).show();
        }
    }

    @Override protected void onDestroy() {
        super.onDestroy();
        executor.shutdownNow();
    }

    // A named marker to avoid adding dependencies for a custom drawable/button library.
    private static class GradientButtonStyle {}
}
