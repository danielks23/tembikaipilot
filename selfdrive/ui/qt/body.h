#pragma once
#include <QWidget>
#include "selfdrive/ui/ui.h"

class BodyWindow : public QWidget {
  Q_OBJECT
public:
  explicit BodyWindow(QWidget* parent = 0);
signals:
  void updateState(const UIState &s);
};
