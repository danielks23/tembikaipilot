#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_6080834398693620578);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1157127680835189021);
void car_H_mod_fun(double *state, double *out_6798648444481860721);
void car_f_fun(double *state, double dt, double *out_2949828160148673620);
void car_F_fun(double *state, double dt, double *out_3046190426194535579);
void car_h_25(double *state, double *unused, double *out_1901206799855987806);
void car_H_25(double *state, double *unused, double *out_4162091519466434527);
void car_h_24(double *state, double *unused, double *out_1632654478212159168);
void car_H_24(double *state, double *unused, double *out_4567189380435876082);
void car_h_30(double *state, double *unused, double *out_8672042026206338742);
void car_H_30(double *state, double *unused, double *out_6680424477973683154);
void car_h_26(double *state, double *unused, double *out_9171386162826735357);
void car_H_26(double *state, double *unused, double *out_420588200592378303);
void car_h_27(double *state, double *unused, double *out_8364114402383816459);
void car_H_27(double *state, double *unused, double *out_4505661166173258243);
void car_h_29(double *state, double *unused, double *out_6962149944233359491);
void car_H_29(double *state, double *unused, double *out_7190655822288075338);
void car_h_28(double *state, double *unused, double *out_2156956614903195404);
void car_H_28(double *state, double *unused, double *out_2108256805218544764);
void car_h_31(double *state, double *unused, double *out_499242341705530838);
void car_H_31(double *state, double *unused, double *out_205619901640973173);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}