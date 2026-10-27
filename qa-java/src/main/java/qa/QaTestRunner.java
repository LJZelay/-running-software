package qa;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public final class QaTestRunner {
    private static final Duration PROCESS_TIMEOUT = Duration.ofSeconds(30);

    private final Path repositoryRoot;
    private final Path pythonExecutable;
    private final List<String> failures = new ArrayList<>();

    private QaTestRunner(Path repositoryRoot) {
        this.repositoryRoot = repositoryRoot;
        this.pythonExecutable = findPythonExecutable(repositoryRoot);
    }

    public static void main(String[] args) throws Exception {
        Path repositoryRoot = args.length == 0
                ? Path.of("").toAbsolutePath().normalize()
                : Path.of(args[0]).toAbsolutePath().normalize();

        QaTestRunner runner = new QaTestRunner(repositoryRoot);
        runner.runAll();

        if (runner.failures.isEmpty()) {
            System.out.println("Java integration QA passed.");
            return;
        }

        System.out.println();
        System.out.println("Java integration QA found " + runner.failures.size() + " issue(s):");
        runner.failures.forEach(failure -> System.out.println(" - " + failure));
        System.exit(1);
    }

    private void runAll() throws IOException, InterruptedException {
        runTest("simulation process", this::simulationProcess);
        runTest("CLI encoding contract", this::cliEncodingContract);
        runTest("CLI event failure exit code", this::cliEventFailureExitCode);
        runTest("summary CSV duration contract", this::summaryCsvDurationContract);
    }

    private void runTest(String name, CheckedTest test) throws IOException, InterruptedException {
        System.out.println("[QA] " + name);
        try {
            test.run();
            System.out.println("     PASS");
        } catch (AssertionError error) {
            failures.add(name + ": " + error.getMessage());
            System.out.println("     FAIL: " + error.getMessage());
        }
    }

    private void simulationProcess() throws IOException, InterruptedException {
        CommandResult result = runPython(
                List.of(
                        "main.py",
                        "--mode",
                        "simulate",
                        "--athletes",
                        "data/athletes.csv",
                        "--events",
                        "data/events.csv"
                ),
                "",
                Map.of()
        );

        assertFalse(result.timedOut(), "simulation timed out");
        assertEquals(0, result.exitCode(), "simulation exit code");
        assertContains(result.output(), "Alice", "simulation output");
        assertContains(result.output(), "Jessica", "simulation output");
    }

    private void cliEncodingContract() throws IOException, InterruptedException {
        CommandResult result = runPython(
                List.of("-m", "controller.cli"),
                "14\n",
                Map.of("PYTHONIOENCODING", "cp1252")
        );

        assertFalse(result.timedOut(), "CLI timed out");
        assertEquals(0, result.exitCode(), "CLI must start under Windows cp1252");
    }

    private void cliEventFailureExitCode() throws IOException, InterruptedException {
        String commands = String.join(
                "\n",
                "2 data/athletes.csv",
                "3 data/events.csv",
                "14",
                ""
        );

        CommandResult result = runPython(
                List.of("-m", "controller.cli"),
                commands,
                Map.of("PYTHONIOENCODING", "utf-8")
        );

        assertFalse(result.timedOut(), "CLI event run timed out");
        assertContains(result.output(), "Errors occurred", "CLI event output");
        assertNotEquals(0, result.exitCode(), "event-processing errors must fail the CLI");
    }

    private void summaryCsvDurationContract() throws IOException, InterruptedException {
        Path temporaryDirectory = Files.createTempDirectory("java-qa-");
        Path summary = temporaryDirectory.resolve("summary.csv");
        try {
            String commands = String.join(
                    "\n",
                    "2 data/athletes.csv",
                    "3 data/events.csv",
                    "4 " + summary,
                    "14",
                    ""
            );

            CommandResult result = runPython(
                    List.of("-m", "controller.cli"),
                    commands,
                    Map.of("PYTHONIOENCODING", "utf-8")
            );

            assertFalse(result.timedOut(), "summary export timed out");
            assertEquals(0, result.exitCode(), "summary export exit code");
            assertTrue(Files.exists(summary), "summary CSV was not created");

            for (String line : Files.readAllLines(summary)) {
                for (String value : line.split(",")) {
                    if (value.matches("-\\d+")) {
                        throw new AssertionError("summary contains negative duration: " + value);
                    }
                }
            }
        } finally {
            Files.deleteIfExists(summary);
            Files.deleteIfExists(temporaryDirectory);
        }
    }

    private CommandResult runPython(
            List<String> scriptArguments,
            String input,
            Map<String, String> environment
    ) throws IOException, InterruptedException {
        List<String> command = new ArrayList<>();
        command.add(pythonExecutable.toString());
        command.addAll(scriptArguments);
        return PythonProcess.run(repositoryRoot, command, input, environment, PROCESS_TIMEOUT);
    }

    private static Path findPythonExecutable(Path repositoryRoot) {
        Path virtualEnvironmentPython = repositoryRoot.resolve(".venv\\Scripts\\python.exe");
        if (Files.isExecutable(virtualEnvironmentPython)) {
            return virtualEnvironmentPython;
        }

        return Path.of("python");
    }

    private static void assertContains(String actual, String expected, String description) {
        if (!actual.contains(expected)) {
            throw new AssertionError(description + " did not contain '" + expected + "'");
        }
    }

    private static void assertEquals(int expected, int actual, String description) {
        if (expected != actual) {
            throw new AssertionError(description + " expected " + expected + " but was " + actual);
        }
    }

    private static void assertNotEquals(int expected, int actual, String description) {
        if (expected == actual) {
            throw new AssertionError(description + " unexpectedly returned " + actual);
        }
    }

    private static void assertTrue(boolean condition, String description) {
        if (!condition) {
            throw new AssertionError(description);
        }
    }

    private static void assertFalse(boolean condition, String description) {
        assertTrue(!condition, description);
    }

    @FunctionalInterface
    private interface CheckedTest {
        void run() throws IOException, InterruptedException;
    }
}
