package qa;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

final class PythonProcess {
    private PythonProcess() {
    }

    static CommandResult run(
            Path repositoryRoot,
            List<String> arguments,
            String input,
            Map<String, String> environment,
            Duration timeout
    ) throws IOException, InterruptedException {
        ProcessBuilder builder = new ProcessBuilder(arguments);
        builder.directory(repositoryRoot.toFile());
        builder.redirectErrorStream(true);
        builder.environment().putAll(environment);

        Process process = builder.start();
        process.getOutputStream().write(input.getBytes(StandardCharsets.UTF_8));
        process.getOutputStream().close();

        ExecutorService outputReader = Executors.newSingleThreadExecutor();
        Future<String> output = outputReader.submit(() -> readOutput(process));
        boolean finished = process.waitFor(timeout.toMillis(), TimeUnit.MILLISECONDS);
        if (!finished) {
            process.destroyForcibly();
            outputReader.shutdownNow();
            return new CommandResult(-1, capturedOutput(output), true);
        }

        String capturedOutput = capturedOutput(output);
        outputReader.shutdown();
        return new CommandResult(process.exitValue(), capturedOutput, false);
    }

    private static String capturedOutput(Future<String> output)
            throws IOException, InterruptedException {
        try {
            return output.get();
        } catch (ExecutionException error) {
            throw new IOException("Unable to capture Python process output", error.getCause());
        }
    }

    private static String readOutput(Process process) throws IOException {
        return new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
    }
}
