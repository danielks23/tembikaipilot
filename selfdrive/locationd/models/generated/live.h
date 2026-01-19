#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void live_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_9(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_12(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_35(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_32(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_update_33(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void live_H(double *in_vec, double *out_6715422720225465196);
void live_err_fun(double *nom_x, double *delta_x, double *out_5615458460679610506);
void live_inv_err_fun(double *nom_x, double *true_x, double *out_5257907782983371139);
void live_H_mod_fun(double *state, double *out_2116159217035017753);
void live_f_fun(double *state, double dt, double *out_6494274572755341641);
void live_F_fun(double *state, double dt, double *out_8055296227808473589);
void live_h_4(double *state, double *unused, double *out_7832709095876608808);
void live_H_4(double *state, double *unused, double *out_8736941391819588899);
void live_h_9(double *state, double *unused, double *out_8392679857130356925);
void live_H_9(double *state, double *unused, double *out_2422583746625515247);
void live_h_10(double *state, double *unused, double *out_4549744337010157578);
void live_H_10(double *state, double *unused, double *out_6171404917023319000);
void live_h_12(double *state, double *unused, double *out_4092371624211471293);
void live_H_12(double *state, double *unused, double *out_4690346273858000922);
void live_h_35(double *state, double *unused, double *out_7566256857397796886);
void live_H_35(double *state, double *unused, double *out_1944783241532987213);
void live_h_32(double *state, double *unused, double *out_5212445838463570525);
void live_H_32(double *state, double *unused, double *out_7884904211520287205);
void live_h_13(double *state, double *unused, double *out_972276733300812660);
void live_H_13(double *state, double *unused, double *out_27692881475922394);
void live_h_14(double *state, double *unused, double *out_8392679857130356925);
void live_H_14(double *state, double *unused, double *out_2422583746625515247);
void live_h_33(double *state, double *unused, double *out_7889011410052119908);
void live_H_33(double *state, double *unused, double *out_3192583619878497737);
void live_predict(double *in_x, double *in_P, double *in_Q, double dt);
}