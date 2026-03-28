package com.normclaim.network;

import com.google.gson.FieldNamingPolicy;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.normclaim.BuildConfig;
import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public final class ApiClient {

    private static ApiService instance;

    private ApiClient() {}

    public static synchronized ApiService get() {
        if (instance == null) {
            HttpLoggingInterceptor log = new HttpLoggingInterceptor();
            log.setLevel(HttpLoggingInterceptor.Level.BASIC);
            OkHttpClient http =
                    new OkHttpClient.Builder().addInterceptor(log).build();

            Gson gson =
                    new GsonBuilder()
                            .setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES)
                            .create();

            Retrofit retrofit =
                    new Retrofit.Builder()
                            .baseUrl(BuildConfig.BASE_URL)
                            .client(http)
                            .addConverterFactory(GsonConverterFactory.create(gson))
                            .build();
            instance = retrofit.create(ApiService.class);
        }
        return instance;
    }
}
