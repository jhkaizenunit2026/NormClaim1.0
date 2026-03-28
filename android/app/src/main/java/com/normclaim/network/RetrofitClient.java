package com.normclaim.network;

import com.google.gson.FieldNamingPolicy;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.normclaim.BuildConfig;
import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

import java.util.concurrent.TimeUnit;

/**
 * Singleton Retrofit client.
 * BASE_URL comes from BuildConfig:
 *   Emulator  → "http://10.0.2.2:8000/"
 *   Physical  → "http://<your-machine-ip>:8000/"
 */
public final class RetrofitClient {

    private static ApiService instance;

    private RetrofitClient() {}

    public static synchronized ApiService get() {
        if (instance == null) {
            HttpLoggingInterceptor log = new HttpLoggingInterceptor();
            log.setLevel(HttpLoggingInterceptor.Level.BODY);

            OkHttpClient http = new OkHttpClient.Builder()
                    .addInterceptor(log)
                    .connectTimeout(30, TimeUnit.SECONDS)
                    .readTimeout(120, TimeUnit.SECONDS)
                    .writeTimeout(60, TimeUnit.SECONDS)
                    .build();

            Gson gson = new GsonBuilder()
                    .setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES)
                    .create();

            Retrofit retrofit = new Retrofit.Builder()
                    .baseUrl(BuildConfig.BASE_URL)
                    .client(http)
                    .addConverterFactory(GsonConverterFactory.create(gson))
                    .build();

            instance = retrofit.create(ApiService.class);
        }
        return instance;
    }
}
