package com.homesoft.openai;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.NoArgsConstructor;
import org.apache.commons.io.FileUtils;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import picocli.CommandLine;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.Callable;

@Builder
@NoArgsConstructor
@AllArgsConstructor
@CommandLine.Command
public class OpenAI implements Callable<Integer> {
    private static final String SCRIPT_DIRECTORY = "openai/src/python/";
    private static final String GENERATE_IMAGE_SCRIPT_NAME = "image_generation.py";
    private static final String VARIATE_IMAGE_SCRIPT_NAME = "image_variation.py";
    private static final String GENERATE_COMPLETION_SCRIPT_NAME = "completion_generation.py";
    private static final String EDIT_TEXT_SCRIPT_NAME = "edit_text.py";
    private static final String DIGEST_ALGORITHM = "SHA-256";
    private static final Logger log = LogManager.getLogger();
    private static final Logger scriptLogger = LogManager.getLogger("script");
    @CommandLine.Option(names = {"--api-key"})
    private String apiKey;

    @CommandLine.Option(names = "--organization")
    private String organization;

    @CommandLine.Option(names = "--request")
    private String request;

    @CommandLine.Option(names = "--user")
    private String user;

    public static void main(String[] args) {
        log.info("Starting OpenAI sample application.");

        final int exitCode = new CommandLine(new OpenAI()).execute(args);
        System.exit(exitCode);
    }

    private static String bytesToHex(byte[] hash) {
        final StringBuilder hexString = new StringBuilder(2 * hash.length);
        for (byte b : hash) {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1) {
                hexString.append('0');
            }
            hexString.append(hex);
        }

        return hexString.toString();
    }

    @SuppressWarnings("unused")
    public Integer call() {
        try {
            final String imageFileName = generateImage();
            log.info("Image has been saved to the file {}", imageFileName);
            return 0;
        } catch (RuntimeException e) {
            log.error("Exception occurred", e);
            return 1;
        }
    }

    public String generateImage() {
        final String hash = getHash(request + System.currentTimeMillis());
        final String outputDirectory = createOutputDirectory(hash);
        saveRequestAttributes(outputDirectory);

        return generate(outputDirectory, GENERATE_IMAGE_SCRIPT_NAME) + ".jpeg";
    }

    public String variateImage(byte[] image) {
        final String hash = getHash(request + System.currentTimeMillis());
        final String outputDirectory = createOutputDirectory(hash);
        saveRequestAttributes(outputDirectory);

        return generate(outputDirectory, VARIATE_IMAGE_SCRIPT_NAME, image) + ".jpeg";
    }

    private String generate(String outputDirectoryPath, String scriptName) {
        return generate(outputDirectoryPath, scriptName, null);
    }

    private String generate(String outputDirectoryPath, String scriptName, byte[] input) {
        final List<String> command = Arrays.asList("python",
                SCRIPT_DIRECTORY + scriptName,
                "--output",
                outputDirectoryPath,
                "--api-key",
                apiKey,
                "--organization",
                organization,
                "--request",
                request,
                "--user",
                user);
        log.info("Executing command: {}", String.join(" ", command));
        final ProcessBuilder processBuilder = new ProcessBuilder(command);
        processBuilder.redirectErrorStream(true);

        try {
            final Process process = processBuilder.start();
            if (null != input) {
                try (final OutputStream outputStream = process.getOutputStream()) {
                    outputStream.write(input);
                }
            }
            final BufferedReader bufferedReader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;
            while (null != (line = bufferedReader.readLine())) {
                scriptLogger.info(line);
            }
            final int exitCode = process.exitValue();
            if (0 != exitCode) {
                log.error("Script execution failed with exit code {}", exitCode);
                deleteOutputDirectory(outputDirectoryPath);
                throw new RuntimeException("Script execution failed with exit code " + exitCode);
            }
        } catch (IOException e) {
            deleteOutputDirectory(outputDirectoryPath);
            throw new RuntimeException("Error happened while executing the script.", e);
        }

        return outputDirectoryPath;
    }

    private void deleteOutputDirectory(String outputDirectory) {
        final boolean deleteDirectoryResult = FileUtils.deleteQuietly(new File(outputDirectory));
        if (!deleteDirectoryResult) {
            log.warn("Couldn't delete directory {}", outputDirectory);
        } else {
            log.info("Deleted directory {} since image generation has failed.", outputDirectory);
        }
    }

    private String createOutputDirectory(String hash) {
        final String outputDirectory = "outputs/" + hash;
        final File directory = new File(outputDirectory);
        if (!directory.mkdirs()) {
            throw new RuntimeException("Couldn't create directory " + outputDirectory);
        }
        return outputDirectory;
    }

    private void saveRequestAttributes(String outputDirectory) {
        final String requestFileName = outputDirectory + File.separator + "request.txt";
        try {
            Files.write(Paths.get(requestFileName), request.getBytes());
        } catch (IOException e) {
            throw new RuntimeException("Couldn't save request into file ", e);
        }

        final String userFileName = outputDirectory + File.separator + "user.txt";
        try {
            Files.write(Paths.get(userFileName), user.getBytes());
        } catch (IOException e) {
            throw new RuntimeException("Couldn't save user name into file ", e);
        }
    }

    private String getHash(String request) {
        try {
            final MessageDigest digest = MessageDigest.getInstance(DIGEST_ALGORITHM);
            return bytesToHex(digest.digest(request.getBytes()));
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("Couldn't get instance of the MessageDigest for " + DIGEST_ALGORITHM, e);
        }
    }

    public String generateTextCompletion() {
        final String hash = getHash(request + System.currentTimeMillis());
        final String outputDirectory = createOutputDirectory(hash);
        saveRequestAttributes(outputDirectory);

        return generate(outputDirectory, GENERATE_COMPLETION_SCRIPT_NAME) + ".txt";
    }

    public String editText(String text) {
        final String hash = getHash(request + System.currentTimeMillis());
        final String outputDirectory = createOutputDirectory(hash);
        saveRequestAttributes(outputDirectory);

        return generate(outputDirectory, EDIT_TEXT_SCRIPT_NAME, text.getBytes(StandardCharsets.UTF_8)) + ".txt";
    }
}
