package com.example.app;

import java.util.List;
import java.util.Map;

public final class Main extends Base implements Runnable {
    private static final int MAX = 42;
    @Override
    public void run() {
        List<String> names = List.of("a", "b");
        Map<String, Integer> counts = new HashMap<>();
        for (String n : names) {
            counts.put(n, counts.getOrDefault(n, 0) + 1);
        }
        System.out.printf("%d items%n", counts.size());
        if (this.enabled && MAX > 10) throw new IllegalStateException("too many");
    }
}
